# Sinaliza API (backend — Fase 1)

Backend em **FastAPI + PostgreSQL** que substitui o `localStorage` mockado do front-end
(`session.js` e `history.js`) por autenticação e histórico persistidos de verdade.

## Como rodar

```bash
cp .env.example .env
# gere um secret real e cole em JWT_SECRET_KEY:
python3 -c "import secrets; print(secrets.token_hex(32))"

docker compose up --build
```

A API sobe em `http://localhost:8000`. Documentação interativa (Swagger) em
`http://localhost:8000/docs`.

## Estrutura

```
app/
  main.py         # cria o app FastAPI, CORS, cria tabelas no startup
  config.py       # variáveis de ambiente (Settings)
  database.py     # engine + sessão SQLAlchemy
  models.py       # User, TranslationHistory
  schemas.py      # contratos de entrada/saída (Pydantic)
  security.py     # hash de senha + JWT
  deps.py         # dependência get_current_user
  routers/
    auth.py       # registro, login, login social (mock), /me
    history.py    # CRUD do histórico de traduções
```

## Endpoints

| Método | Rota                        | Auth | Descrição |
|--------|-----------------------------|:---:|-----------|
| POST   | `/auth/register`            | não | Cria conta com e-mail/senha |
| POST   | `/auth/login`                | não | Login com e-mail/senha |
| POST   | `/auth/social`               | não | Login Google/Apple — **mock**, ver TODO abaixo |
| GET    | `/auth/me`                   | sim | Dados do usuário logado |
| GET    | `/history?type=&favorite=&search=` | sim | Lista histórico (com filtros) |
| POST   | `/history`                   | sim | Cria um registro |
| PATCH  | `/history/{id}/favorite`     | sim | Alterna favorito |
| DELETE | `/history/{id}`              | sim | Remove um registro |
| DELETE | `/history`                   | sim | Limpa todo o histórico |

Rotas autenticadas esperam `Authorization: Bearer <token>`, onde `<token>` é o
`access_token` retornado por `/auth/register`, `/auth/login` ou `/auth/social`.

## ⚠️ Pendências antes de produção

1. **Login social é mock.** `/auth/social` confia no `name`/`email` enviados pelo
   cliente, igual ao front-end mock atual (`apple.html`/`google.html`). Antes de expor
   isso publicamente, implemente a verificação real (comentário `TODO` em
   `app/routers/auth.py`):
   - Google: validar o `id_token` do Google Identity Services com `google-auth`.
   - Apple: validar o `identity_token` (JWT) contra as chaves JWKS da Apple.
2. **Migrações:** hoje as tabelas são criadas com `Base.metadata.create_all` no
   startup — ótimo para desenvolver rápido, mas isso não altera colunas de tabelas já
   existentes. Assim que o schema estabilizar um pouco, rode `alembic init` e passe a
   versionar as migrações.
3. **CORS:** ajuste `CORS_ORIGINS` no `.env` para o domínio real do front-end em produção.

## Próximo passo (integração com o front-end)

Quando este backend estiver rodando, o próximo passo é trocar, no front-end:
- `session.js`: `login()`/`getCurrentUser()` passam a chamar `/auth/login`,
  `/auth/social` etc., guardando o `access_token` (em vez do objeto de usuário) e
  enviando-o no header `Authorization` das próximas chamadas.
- `history.js`: `getHistory()`, `addHistoryEntry()`, `toggleHistoryFavorite()`,
  `clearHistory()` passam a chamar os endpoints de `/history` em vez de `Storage`.

Isso é rápido porque o front-end já está organizado em módulos com essas funções
isoladas — é troca de implementação, não de interface. Posso montar esse cliente de
API (`js/api.js`) e a atualização de `session.js`/`history.js` quando você quiser.
