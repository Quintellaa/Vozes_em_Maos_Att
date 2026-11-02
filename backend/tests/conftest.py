"""Configuração comum dos testes.

Cada execução usa um banco SQLite novo e temporário, então os testes nunca
mexem no sinaliza.db de desenvolvimento.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))  # permite `from app...` rodando `pytest` de dentro de backend/

# Precisa vir ANTES de importar o app: config.py lê as variáveis na importação.
_db_file = Path(tempfile.gettempdir()) / f"sinaliza_test_{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["MODEL_PATH"] = str(BACKEND_DIR / "models" / "libras_pose_hands.joblib")
os.environ["JWT_SECRET_KEY"] = "segredo-so-para-testes"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # o "with" dispara o startup (cria as tabelas)
        yield c
    _db_file.unlink(missing_ok=True)


@pytest.fixture
def auth_headers(client):
    """Cria um usuário novo a cada teste e devolve o header de autenticação."""
    email = f"user_{uuid.uuid4().hex[:8]}@teste.com"
    r = client.post("/auth/register", json={"name": "Usuário Teste", "email": email, "password": "123456"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
