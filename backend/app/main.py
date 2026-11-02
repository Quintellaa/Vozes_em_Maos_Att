"""Ponto de entrada da API Sinaliza."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, SessionLocal, engine
from sqlalchemy import inspect, text

from app.routers import auth, communities, history, recognition, users

app = FastAPI(title="Sinaliza API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(history.router)
app.include_router(recognition.router)
app.include_router(communities.router)
app.include_router(users.router)


def _add_missing_user_columns():
    """create_all não adiciona colunas em tabelas que já existem. Enquanto o projeto não usa
    migrações do Alembic, adicionamos aqui as colunas da foto de perfil no sinaliza.db antigo."""
    existing = {col["name"] for col in inspect(engine).get_columns("users")}
    binary = "BYTEA" if engine.dialect.name == "postgresql" else "BLOB"
    new_columns = {"avatar": binary, "avatar_type": "VARCHAR(20)", "avatar_updated_at": "BIGINT"}
    with engine.begin() as conn:
        for name, sql_type in new_columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sql_type}"))


@app.on_event("startup")
def on_startup():
    # MVP: cria as tabelas automaticamente se não existirem.
    # Antes de produção, troque por migrações versionadas com Alembic
    # (create_all não sabe alterar colunas de tabelas já existentes).
    Base.metadata.create_all(bind=engine)
    _add_missing_user_columns()
    # Cria as comunidades iniciais (só na primeira vez, com o banco vazio).
    with SessionLocal() as db:
        communities.seed_default_communities(db)


@app.get("/health", tags=["health"])
def health_check():
    # "database" mostra qual banco está em uso: na nuvem tem que ser "postgresql".
    # Se aparecer "sqlite" lá, as contas somem toda vez que o servidor reinicia.
    return {"status": "ok", "database": engine.dialect.name}


# O próprio backend entrega o front-end (a pasta frontend/), pra o app funcionar
# num endereço só — é assim que roda na nuvem e no celular. Montado por último:
# as rotas da API acima têm prioridade. Localmente, o Live Server continua valendo.
_frontend_dir = next(
    (p for p in (Path(settings.frontend_dir) if settings.frontend_dir else None,
                 Path(__file__).resolve().parents[2] / "frontend")
     if p and p.is_dir()),
    None,
)
if _frontend_dir:
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
