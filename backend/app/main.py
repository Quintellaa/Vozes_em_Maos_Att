"""Ponto de entrada da API Sinaliza."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, history, recognition

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


@app.on_event("startup")
def on_startup():
    # MVP: cria as tabelas automaticamente se não existirem.
    # Antes de produção, troque por migrações versionadas com Alembic
    # (create_all não sabe alterar colunas de tabelas já existentes).
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
