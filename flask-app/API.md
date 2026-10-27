# Documentação da API

## Convenções

- Os exemplos usam `http://localhost:5000` como endereço-base. Troque-o pelo
  endereço do servidor.
- A API aceita chamadas CORS de qualquer origem. Isso não remove a autenticação:
  as rotas sob `/licitacoes` continuam exigindo um JWT no header `Authorization`.
- Os corpos JSON devem ser enviados com `Content-Type: application/json`.
- As rotas sob `/licitacoes` exigem autenticação. Envie o token JWT retornado
  pelo login no header `Authorization: Bearer <token>`.
- A rota de criação de conta (`POST /auth/criar-conta`) está desativada. O
  usuário precisa já existir na collection de usuários do MongoDB.

## Login

Autentica um usuário e retorna um JWT para uso nas rotas protegidas.

**Requisição**

```http
POST /auth/login
Content-Type: application/json
```

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `email` | string | Sim | E-mail cadastrado. A comparação ignora maiúsculas/minúsculas e espaços nas extremidades. |
| `senha` | string | Sim | Senha do usuário. |

```json
{
  "email": "usuario@exemplo.com",
  "senha": "senha-do-usuario"
}
```

**Resposta de sucesso — `200 OK`**

```json
{
  "usuario": {
    "id": "65f...",
    "email": "usuario@exemplo.com"
  },
  "token": "<jwt>"
}
```

O token expira conforme `JWT_EXPIRACAO_SEGUNDOS` (padrão: 3600 segundos).

**Erros**

- `400 Bad Request`: corpo inválido/não JSON ou campo `email`/`senha` ausente.
- `401 Unauthorized`: usuário não encontrado ou senha incorreta.

## Listagem de licitações salvas

Retorna licitações já armazenadas no MongoDB, ordenadas da mais recentemente
processada para a mais antiga. Esta rota **não** busca novas licitações no PNCP
nem inicia análise.

**Requisição**

```http
GET /licitacoes?page=1&page_size=10
Authorization: Bearer <jwt>
```

| Parâmetro | Local | Tipo | Obrigatório | Padrão | Descrição |
|---|---|---|---:|---:|---|
| `page` | query | inteiro | Não | `1` | Página (mínimo efetivo: 1). |
| `page_size` | query | inteiro | Não | `10` | Itens por página (limitado ao intervalo de 1 a 100). |
| `id` | query | string | Não | — | Filtra pelo número de controle PNCP. |

**Resposta de sucesso — `200 OK`**

```json
{
  "items": [
    {
      "numero_controle_pncp": "12345678901234567890",
      "licitacao": {},
      "arquivo": {},
      "resumo_edital": ["Resposta da análise"],
      "status": "PROCESSADO",
      "processado_em": "2026-10-26T18:00:00+00:00"
    }
  ],
  "page": 1,
  "page_size": 10,
  "total": 1,
  "total_pages": 1
}
```

`licitacao` e `arquivo` contêm os dados recebidos das integrações; seus campos
dependem do registro no PNCP. `resumo_edital` contém as respostas da análise.
Quando não há resultados, `items` é uma lista vazia e `total`/`total_pages`
serão zero.

**Erros**

- `401 Unauthorized`: token ausente, inválido ou expirado.

## Analisar licitação por ID

Busca a licitação no PNCP pelo número de controle, localiza o edital e o
processa. O identificador vai no caminho da URL.

**Requisição**

```http
POST /licitacoes/analisar/<numero_controle_pncp>
Authorization: Bearer <jwt>
```

| Parâmetro | Local | Tipo | Obrigatório | Descrição |
|---|---|---|---:|---|
| `numero_controle_pncp` | caminho | string | Sim | Número de controle da licitação no PNCP. |

Não é necessário enviar corpo.

**Resposta de sucesso**

```json
{
  "licitacao": {},
  "arquivo": {},
  "resumo_edital": ["Resposta da análise"],
  "status": "PROCESSADO"
}
```

O comportamento depende de a licitação já estar salva e da configuração
`ASYNC_LICITATION_SUMMARY_ENABLED`:

- Se já estiver processada, retorna o documento existente sem baixar e analisar
  novamente o edital.
- Com o modo assíncrono desativado (padrão), baixa e analisa o edital antes de
  responder. `resumo_edital` contém as respostas geradas.
- Com `ASYNC_LICITATION_SUMMARY_ENABLED=true`, salva inicialmente o documento
  como `PENDENTE` e dispara o workflow `processar-resumo.yml`, enviando o número
  de controle PNCP. O workflow busca os dados no MongoDB, executa o
  processamento e atualiza resumo e status para `PROCESSADO`. A resposta
  imediata contém `resumo_edital: []`; consulte depois a listagem para obter o
  resumo atualizado.

O campo `status` será `PENDENTE` enquanto o resumo aguarda ou está em
processamento, e `PROCESSADO` após a geração do resumo e sua gravação no banco.
No modo assíncrono, a resposta imediata da análise terá `status: "PENDENTE"`;
consulte a listagem para acompanhar o valor atualizado.

O modo assíncrono requer `GITHUB_ACTIONS_TOKEN` no serviço, com permissão para
executar workflows no repositório definido por `GITHUB_ACTIONS_REPOSITORY`.
`GITHUB_ACTIONS_REF` define a branch usada (padrão: `main`). O token JWT da API
não é encaminhado ao workflow.

No Render, habilite `ASYNC_LICITATION_SUMMARY_ENABLED=true` e configure
`GITHUB_ACTIONS_TOKEN` com um token do GitHub que tenha permissão `Actions:
write` no repositório. No GitHub, o workflow precisa estar na branch informada
em `GITHUB_ACTIONS_REF`.

Configure também estes GitHub Actions secrets no repositório:

- `MONGO_URI`
- `OPENROUTER_API_KEY`
- `MONGO_DATABASE` e `MONGO_COLLECTION_LICITACOES` se forem diferentes dos
  padrões `licitacoes_db` e `licitacoes`
- `PNCP_COOKIE` se a integração com o PNCP exigir cookie

**Erros**

- `400 Bad Request`: erro de validação do serviço, retornado como `{"erro": "..."}`.
- `401 Unauthorized`: token ausente, inválido ou expirado.
- `404 Not Found`: licitação não encontrada no PNCP ou sem edital disponível.

## Exemplos com cURL

```bash
curl -X POST http://localhost:5000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"usuario@exemplo.com","senha":"senha-do-usuario"}'
```

Use o valor de `token` retornado no login:

```bash
curl 'http://localhost:5000/licitacoes?page=1&page_size=10' \
  -H 'Authorization: Bearer <jwt>'
```

```bash
curl -X POST \
  'http://localhost:5000/licitacoes/analisar/12345678901234567890' \
  -H 'Authorization: Bearer <jwt>'
```
