import logging
from datetime import date

import requests
from flask import current_app

from app.extensions import db
from app.models.relatorio import Relatorio

logger = logging.getLogger(__name__)


def _gerar_placeholder(submissao):
    """Gera um relatório realista pré-programado ("mock") para a equipe de Front-End trabalhar."""
    return (
        "# Pontos Fortes:\n"
        "- **Reação sob pressão:** O candidato demonstra uma abordagem equilibrada ao tentar manter a calma e, crucialmente, valorizar a colaboração com a equipe. Isso indica autoconsciência e reconhecimento da força coletiva, características essenciais para uma liderança eficaz e ética.\n"
        "- **Lidar com atrasos:** A postura de informar a gerência imediatamente reflete um alto nível de transparência, honestidade e responsabilidade. Essas qualidades são fundamentais para construir confiança.\n\n"
        "# Pontos Fracos:\n"
        "- Nenhum ponto fraco significativo ou área de risco foi identificada com base nas respostas fornecidas.\n\n"
        "# Conclusão:\n"
        f"O candidato demonstrou um perfil ético robusto e promissor. A pontuação total de {submissao.pontuacao}, aliada à qualidade das respostas, sugere que o candidato está bem alinhado com os princípios éticos esperados e apto para assumir responsabilidades que demandem integridade e liderança colaborativa."
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
    """Extrai robustamente o texto da resposta do agente em vários formatos retornados."""
    if isinstance(response_json, list) and len(response_json) > 0:
        # A API do ADK retorna a lista completa de interações da sessão; o último é a resposta final
        last_item = response_json[-1]
        if isinstance(last_item, dict):
            content = last_item.get("content", {})
            parts = content.get("parts", [])
            if parts and isinstance(parts, list):
                text = parts[0].get("text")
                if text:
                    return text
    elif isinstance(response_json, dict):
        content = response_json.get("content", {})
        parts = content.get("parts", [])
        if parts and isinstance(parts, list):
            text = parts[0].get("text")
            if text:
                return text
        resp = response_json.get("response", {})
        if isinstance(resp, dict) and "text" in resp:
            return resp["text"]
        if "text" in response_json:
            return response_json["text"]
            
    raise ValueError("Formato de resposta do agente de IA inválido ou texto não encontrado.")


def gerar_relatorio_ia(submissao):
    """
    Realiza a chamada HTTP para o agente de IA real e persiste o relatório no banco de dados.
    """
    agent_url = (current_app.config.get("AI_AGENT_URL") or "https://azuos-adk-agent-97yo.onrender.com").rstrip("/")
    app_name = current_app.config.get("AI_APP_NAME", "azuos_compliance_beta")
    user_id = f"u_{submissao.usuario_id}"
    session_id = f"s_{submissao.submissao_id}"
    
    logger.info(f"Conectando ao agente de IA em {agent_url} para submissão {submissao.submissao_id}")
    
    # 1. CRIAR SESSÃO
    session_url = f"{agent_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}"
    try:
        logger.info(f"Criando sessão do agente: {session_url}")
        resp_session = requests.post(session_url, timeout=60)
        resp_session.raise_for_status()
        logger.info("Sessão criada com sucesso no agente!")
    except Exception as e:
        logger.warning(f"Erro ao criar sessão no agente: {e}. Continuando com o envio da mensagem.")

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
        logger.error(f"Falha na comunicação com o agente de IA: {e}. Gerando relatório mock de fallback.")
        conteudo = _gerar_placeholder(submissao) + "\n\n*⚠️ NOTA: Este relatório foi gerado automaticamente usando dados simulados devido a uma falha de conexão com o agente de IA real.*"
        
    relatorio = Relatorio(
        conteudo=conteudo, 
        data_criacao=date.today(),
        submissao_id=submissao.submissao_id,
    )
    db.session.add(relatorio)
    db.session.commit()
    return relatorio