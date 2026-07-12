import logging
import time
from datetime import date

import requests
from flask import current_app

from app.extensions import db
from app.models.relatorio import Relatorio

logger = logging.getLogger(__name__)


def _gerar_placeholder(submissao):
    """Gera um relatório realista pré-programado ("mock") para a equipe de Front-End trabalhar."""
    pontuacao_calculada = sum(
        (r.pergunta.pontuacao if (r.pergunta and r.pergunta.pontuacao is not None) else 0)
        for r in submissao.respostas
    )
    pontuacao_total = submissao.pontuacao if submissao.pontuacao is not None else pontuacao_calculada

    return (
        "# Pontuação Geral:\n"
        f"O candidato obteve {pontuacao_total} pontos, valor considerado dentro da faixa esperada com base nas respostas fornecidas.\n\n"
        "# Pontos Positivos:\n"
        "- **Reação sob pressão:** O candidato demonstra uma abordagem equilibrada ao tentar manter a calma e, crucialmente, valorizar a colaboração com a equipe. Isso indica autoconsciência e reconhecimento da força coletiva, características essenciais para uma liderança eficaz e ética.\n"
        "- **Lidar com atrasos:** A postura de informar a gerência imediatamente reflete um alto nível de transparência, honestidade e responsabilidade. Essas qualidades são fundamentais para construir confiança.\n\n"
        "# Pontos Negativos (a melhorar):\n"
        "- Nenhum ponto fraco significativo ou área de risco foi identificada com base nas respostas fornecidas.\n\n"
        "# Conclusão:\n"
        f"O candidato demonstrou um perfil ético robusto e promissor. A pontuação total de {pontuacao_total}, aliada à qualidade das respostas, sugere que o candidato está bem alinhado com os princípios éticos esperados e apto para assumir responsabilidades que demandem integridade e liderança colaborativa."
    )


def construir_prompt(submissao):
    """Constrói o prompt de texto de forma dinâmica contendo as respostas da submissão."""
    usuario_nome = submissao.usuario.nome if (submissao.usuario and submissao.usuario.nome) else "Desconhecido"
    usuario_id = submissao.usuario_id
    formulario_titulo = submissao.formulario.titulo if (submissao.formulario and submissao.formulario.titulo) else "Desconhecido"
    pontuacao_total = submissao.pontuacao or 0

    texto_payload = f"""Avalie a seguinte submissão de formulário e gere um relatório de perfil ético.

Usuário: {usuario_nome} (ID: {usuario_id})
Formulário: {formulario_titulo}
Pontuação Total: {pontuacao_total}

Respostas:"""

    for r in submissao.respostas:
        pergunta_texto = r.pergunta.pergunta if (r.pergunta and r.pergunta.pergunta) else "Pergunta sem texto"
        pergunta_pontos = r.pergunta.pontuacao if (r.pergunta and r.pergunta.pontuacao is not None) else 0
        texto_payload += f"\n- Pergunta: {pergunta_texto}\n  Resposta: {r.resposta} (Pontos: {pergunta_pontos})"
        
    return texto_payload


def extrair_texto_resposta(response_json):
    """Extrai robustamente o texto da resposta do agente em vários formatos retornados.

    IMPORTANTE: quando o agente usa sub-agentes/ferramentas (ex: consulta ao Código de Ética)
    antes ou durante a geração do relatório, o /run do ADK retorna VÁRIOS eventos de sessão
    (function_call, function_response, e um ou mais turnos de texto do modelo). O relatório
    final pode estar espalhado por múltiplos turnos de texto, não apenas no último evento.
    Por isso, concatenamos o texto de TODOS os turnos do modelo (role != "user"), na ordem
    em que aparecem, e ignoramos partes sem texto (ex: function_call/function_response).
    """
    if isinstance(response_json, list) and len(response_json) > 0:
        textos = []
        for item in response_json:
            if not isinstance(item, dict):
                continue
            content = item.get("content", {})
            if not isinstance(content, dict):
                continue
            role = content.get("role")
            if role == "user":
                # ignora o eco da própria mensagem enviada por nós
                continue
            parts = content.get("parts", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                if isinstance(part, dict):
                    texto_part = part.get("text")
                    if texto_part:
                        textos.append(texto_part)
        if textos:
            return "\n".join(textos)
    elif isinstance(response_json, dict):
        content = response_json.get("content", {})
        parts = content.get("parts", [])
        if parts and isinstance(parts, list):
            textos = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
            if textos:
                return "\n".join(textos)
        resp = response_json.get("response", {})
        if isinstance(resp, dict) and "text" in resp:
            return resp["text"]
        if "text" in response_json:
            return response_json["text"]

    raise ValueError("Formato de resposta do agente de IA inválido ou texto não encontrado.")


def _log_erro_http(prefixo, e):
    """Loga status code e corpo da resposta quando disponível, em vez de só a exceção genérica."""
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        logger.error(f"{prefixo}: HTTP {e.response.status_code} - corpo: {e.response.text[:1000]}")
    elif isinstance(e, requests.exceptions.Timeout):
        logger.error(f"{prefixo}: timeout - {e}")
    elif isinstance(e, requests.exceptions.ConnectionError):
        logger.error(f"{prefixo}: erro de conexão - {e}")
    else:
        logger.error(f"{prefixo}: {e}")


def _acordar_agente(agent_url, tentativas=6, intervalo=10, timeout_por_tentativa=15):
    """
    Faz ping em /docs para 'acordar' o serviço (free tier do Render hiberna após inatividade
    e pode levar 30-50s+ para responder de novo). Tenta várias vezes até o serviço responder
    ou até esgotar as tentativas. Retorna True se o serviço respondeu, False caso contrário.
    """
    docs_url = f"{agent_url}/docs"
    for tentativa in range(1, tentativas + 1):
        try:
            logger.info(f"Verificando se o agente está no ar (tentativa {tentativa}/{tentativas}): {docs_url}")
            resp = requests.get(docs_url, timeout=timeout_por_tentativa)
            if resp.status_code == 200:
                logger.info("Agente está no ar e respondendo.")
                return True
            logger.warning(f"Agente respondeu com status inesperado: {resp.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Agente ainda não respondeu (tentativa {tentativa}/{tentativas}): {e}")

        if tentativa < tentativas:
            time.sleep(intervalo)

    logger.error("Agente não respondeu após todas as tentativas de wake-up.")
    return False


def gerar_relatorio_ia(submissao):
    """
    Realiza a chamada HTTP para o agente de IA real e persiste o relatório no banco de dados.
    """
    agent_url = (current_app.config.get("AI_AGENT_URL") or "https://azuos-adk-agent-97yo.onrender.com").rstrip("/")
    app_name = current_app.config.get("AI_APP_NAME", "azuos_compliance_beta")
    user_id = f"u_{submissao.usuario_id}"
    session_id = f"s_{submissao.submissao_id}"

    logger.info(f"Conectando ao agente de IA em {agent_url} para submissão {submissao.submissao_id}")

    # 0. ACORDAR O AGENTE (evita timeout por cold start do Render free tier)
    agente_no_ar = _acordar_agente(agent_url)
    if not agente_no_ar:
        conteudo = _gerar_placeholder(submissao) + "\n\n*⚠️ NOTA: Este relatório foi gerado automaticamente usando dados simulados pois o agente de IA não respondeu ao ser acordado.*"
        relatorio = Relatorio(
            conteudo=conteudo,
            data_criacao=date.today(),
            submissao_id=submissao.submissao_id,
        )
        db.session.add(relatorio)
        db.session.commit()
        return relatorio

    # 1. CRIAR SESSÃO
    session_url = f"{agent_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}"
    try:
        logger.info(f"Criando sessão do agente: {session_url}")
        resp_session = requests.post(session_url, timeout=60)
        resp_session.raise_for_status()
        logger.info("Sessão criada com sucesso no agente!")
    except Exception as e:
        _log_erro_http("Erro ao criar sessão no agente (continuando com o envio da mensagem)", e)

    # 2. ENVIAR A MSG (O RUN)
    run_url = f"{agent_url}/run"
    texto_payload = construir_prompt(submissao)
    
    payload = {
        "appName": app_name,
        "userId": user_id,
        "sessionId": session_id,
        "newMessage": {
            "role": "user",
            "parts": [{"text": texto_payload}]
        }
    }
    
    try:
        logger.info("Enviando dados da submissão para a IA...")
        resp_run = requests.post(run_url, json=payload, timeout=60)
        resp_run.raise_for_status()
        
        response_json = resp_run.json()
        conteudo = extrair_texto_resposta(response_json)
        logger.info("Relatório gerado com sucesso pelo agente de IA.")
        
    except Exception as e:
        _log_erro_http("Falha na comunicação com o agente de IA (gerando relatório mock de fallback)", e)
        conteudo = _gerar_placeholder(submissao) + "\n\n*⚠️ NOTA: Este relatório foi gerado automaticamente usando dados simulados devido a uma falha de conexão com o agente de IA real.*"
        
    relatorio = Relatorio(
        conteudo=conteudo, 
        data_criacao=date.today(),
        submissao_id=submissao.submissao_id,
    )
    db.session.add(relatorio)
    db.session.commit()
    return relatorio