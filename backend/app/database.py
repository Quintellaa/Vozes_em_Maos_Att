"""Conexão com o banco de dados via SQLAlchemy.

Funciona tanto com SQLite (uso local, sem instalar nada) quanto com PostgreSQL
(quando você quiser subir com Docker de novo, mais pra frente) — só depende do
valor de DATABASE_URL no .env.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# SQLite exige essa flag quando usado com FastAPI (que acessa a conexão em
# threads diferentes); Postgres não precisa e por isso fica de fora nesse caso.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency do FastAPI: abre uma sessão por request e garante o fechamento."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
