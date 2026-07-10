# Documentação da API REST - Azuos

Esta documentação tem como objetivo guiar a equipe de Frontend no consumo correto dos endpoints da aplicação. Todas as requisições devem ser feitas para a **Base URL**.

**Base URL**: `https://flask-api-production-b69d.up.railway.app`

---

## 🟢 Health Check
Verifica se a API está online e respondendo.

### GET `/api/health`
- **Descrição:** Retorna o status da aplicação.
- **Resposta Sucesso (200):**
  ```json
  { "status": "ok" }
  ```

---

## 🔐 Autenticação

### POST `/api/auth/login`
- **Descrição:** Realiza o login do usuário.
- **Corpo da Requisição (JSON):**
  ```json
  {
    "email": "usuario@exemplo.com",
    "senha": "sua_senha"
  }
  ```
- **Resposta Sucesso (200):** Retorna os dados do usuário autenticado.
- **Erros:** 
  - `400`: Email e senha são obrigatórios.
  - `401`: Credenciais inválidas.

---

## 👥 Usuários
Gestão de usuários (funcionários, líderes e administradores).

### GET `/api/usuarios`
- **Descrição:** Retorna todos os usuários cadastrados.

### GET `/api/usuarios/<id>`
- **Descrição:** Retorna um usuário específico.
- **Erros:** `404` se não encontrado.

### POST `/api/usuarios`
- **Descrição:** Cria um novo usuário.
- **Corpo da Requisição (JSON):**
  ```json
  {
    "nome": "João da Silva",
    "cpf": "12345678900",
    "email": "joao@email.com",
    "role_id": 1,
    "senha": "senha_segura",
    "lider": false,          // opcional
    "departamento_id": 2     // opcional
  }
  ```
- **Erros:** `400` para campos faltando, `409` se CPF ou Email já existirem.

### PUT `/api/usuarios/<id>`
- **Descrição:** Atualiza os dados de um usuário existente. Envie apenas os campos que deseja alterar.

### DELETE `/api/usuarios/<id>`
- **Descrição:** Remove um usuário do sistema.

---

## 🏢 Departamentos
Gestão de departamentos da empresa.

### GET `/api/departamentos`
- **Descrição:** Lista todos os departamentos.

### GET `/api/departamentos/<id>`
- **Descrição:** Retorna um departamento específico.

### POST `/api/departamentos`
- **Descrição:** Cria um departamento.
- **Corpo:** `{ "nome": "Vendas" }`

### PUT `/api/departamentos/<id>`
- **Descrição:** Atualiza o departamento.
- **Corpo:** `{ "nome": "Novo Nome" }`

### DELETE `/api/departamentos/<id>`
- **Descrição:** Remove o departamento.

---

## 💼 Cargos
Gestão de cargos (roles).

### GET `/api/cargos`
- **Descrição:** Lista todos os cargos.

### GET `/api/cargos/<id>`
- **Descrição:** Retorna um cargo específico.

### POST `/api/cargos`
- **Descrição:** Cria um cargo.
- **Corpo:** `{ "nome": "Gerente" }`

### PUT `/api/cargos/<id>`
- **Descrição:** Atualiza o cargo.
- **Corpo:** `{ "nome": "Novo Nome" }`

### DELETE `/api/cargos/<id>`
- **Descrição:** Remove o cargo.

---

## 📋 Formulários
Gestão de formulários de avaliação ética.

### GET `/api/formularios`
- **Descrição:** Lista todos os formulários.

### GET `/api/formularios/<id>`
- **Descrição:** Retorna um formulário específico. **Inclui as perguntas** relacionadas a ele no retorno JSON.

### GET `/api/formularios/por-cargo/<role_id>`
- **Descrição:** Lista os formulários atribuídos a um cargo específico (inclui perguntas no retorno).

### POST `/api/formularios`
- **Descrição:** Cria um formulário.
- **Corpo:** 
  ```json
  {
    "titulo": "Avaliação Ética Nível 1",
    "role_id": 2
  }
  ```

### PUT `/api/formularios/<id>`
- **Descrição:** Atualiza o formulário.

### DELETE `/api/formularios/<id>`
- **Descrição:** Remove o formulário.

---

## ❓ Perguntas
Gestão das perguntas dentro dos formulários.

### GET `/api/perguntas`
- **Descrição:** Lista perguntas. 
- **Query Params (Opcional):** `?formulario_id=<id>` (Filtra as perguntas por formulário).

### GET `/api/perguntas/<id>`
- **Descrição:** Retorna uma pergunta específica.

### POST `/api/perguntas`
- **Descrição:** Cria uma pergunta vinculada a um formulário.
- **Corpo:**
  ```json
  {
    "pergunta": "O que você faria na situação X?",
    "formulario_id": 1,
    "pontuacao": 10   // opcional
  }
  ```

### PUT `/api/perguntas/<id>`
- **Descrição:** Atualiza a pergunta.

### DELETE `/api/perguntas/<id>`
- **Descrição:** Remove a pergunta.

---

## 📝 Submissões (Envio do Formulário)
O processo central de envio do formulário preenchido por um usuário.

### POST `/api/submissoes`
> [!IMPORTANT]
> **Endpoint Crítico:** Cria a submissão, salva as respostas do usuário e dispara automaticamente o Agente de Inteligência Artificial para gerar o Relatório de Perfil Ético.

- **Corpo da Requisição (JSON):**
  ```json
  {
    "usuario_id": 3,
    "formulario_id": 1,
    "respostas": [
      {
        "pergunta_id": 1,
        "resposta": "Minha resposta descritiva aqui..."
      },
      {
        "pergunta_id": 2,
        "resposta": "Outra resposta..."
      }
    ]
  }
  ```
- **Resposta Sucesso (201):** Retorna os dados da submissão com o relatório de IA incorporado no JSON (em `relatorio`).

### GET `/api/submissoes`
- **Descrição:** Lista todas as submissões.

### GET `/api/submissoes/<id>`
- **Descrição:** Retorna uma submissão específica, incluindo as respostas dadas.

### GET `/api/submissoes/usuario/<usuario_id>`
- **Descrição:** Lista todas as submissões feitas por um usuário específico.

### PUT `/api/submissoes/<id>` e DELETE `/api/submissoes/<id>`
- **Descrição:** Edita ou apaga uma submissão inteira.

---

## ✍️ Respostas
*(Geralmente inseridas via `/api/submissoes` POST, mas podem ser manipuladas diretamente).*

### GET `/api/respostas`
- **Query Params:** `?submissao_id=<id>`

### GET, POST, PUT, DELETE `/api/respostas/<id>`
- **Descrição:** Manipulação direta de uma resposta.

---

## 📊 Relatórios (Resultados da IA)
Geralmente gerados pelo Agente de Inteligência artificial via `POST /api/submissoes`.

### GET `/api/relatorios`
- **Descrição:** Lista todos os relatórios gerados.

### GET `/api/relatorios/<id>`
- **Descrição:** Retorna um relatório específico.

### GET `/api/relatorios/submissao/<submissao_id>`
- **Descrição:** Busca o relatório gerado especificamente para uma submissão.

### POST, PUT, DELETE `/api/relatorios`
- **Descrição:** Criação manual, edição ou deleção do texto de um relatório.
