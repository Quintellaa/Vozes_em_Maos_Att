# Sinaliza API (backend — Fase 1)

Backend em **FastAPI + SQLite** (PostgreSQL opcional via Docker) que substitui o `localStorage` mockado do front-end
(`session.js` e `history.js`) por autenticação e histórico persistidos de verdade.

## Como rodar (local, com SQLite — o jeito mais simples)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. Documentação interativa (Swagger) em
`http://localhost:8000/docs`. O banco é o arquivo `sinaliza.db`, criado sozinho.

O front-end é estático: abra `frontend/index.html` com o Live Server do VS Code
(porta 5500/5501, já liberadas no CORS do `.env.example`).

## Como rodar (Docker, com PostgreSQL)

No `.env`, troque `DATABASE_URL=postgresql://sinaliza:sinaliza@db:5432/sinaliza` e:

```bash
docker compose up --build
```

## Testes

```bash
cd backend
pytest -q
```

16 testes cobrindo cadastro/login, histórico (inclusive que um usuário não enxerga
o histórico de outro), a extração de características e a rota `/recognition`.
Cada execução usa um banco temporário — não mexe no `sinaliza.db`.

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
    recognition.py  # Libras → texto: recebe landmarks, aplica o modelo
  libras_features.py  # landmarks → vetor de características (igual ao do treino)
models/
  libras_pose_hands.joblib  # modelo treinado (20 sinais, MINDS-Libras)
tests/              # pytest
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
| POST   | `/recognition/predict`       | sim | Frames de landmarks → sinal + confiança |
| GET    | `/recognition/info`          | sim | Modelo disponível? Quais sinais conhece |

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
