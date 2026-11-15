"""Testes de cadastro, login e sessão."""


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_me(client):
    dados = {"name": "Ana Souza", "email": "ana@teste.com", "password": "senha123"}
    r = client.post("/auth/register", json=dados)
    assert r.status_code == 201
    assert r.json()["user"]["handle"] == "ana"  # handle vem do e-mail

    r = client.post("/auth/login", json={"email": "ana@teste.com", "password": "senha123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["email"] == "ana@teste.com"


def test_email_duplicado_retorna_409(client):
    dados = {"name": "Bia", "email": "bia@teste.com", "password": "senha123"}
    assert client.post("/auth/register", json=dados).status_code == 201
    assert client.post("/auth/register", json=dados).status_code == 409


def test_senha_errada_retorna_401(client):
    client.post("/auth/register", json={"name": "Caio", "email": "caio@teste.com", "password": "certa123"})
    r = client.post("/auth/login", json={"email": "caio@teste.com", "password": "errada"})
    assert r.status_code == 401


def test_rota_protegida_sem_token_retorna_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer token-falso"}).status_code == 401


def test_email_sem_diferenciar_maiusculas(client):
    r = client.post("/auth/register", json={"name": "Duda", "email": "Duda.Lima@Teste.com", "password": "senha123"})
    assert r.status_code == 201
    assert client.post("/auth/login", json={"email": "duda.lima@teste.com", "password": "senha123"}).status_code == 200
    assert client.post("/auth/register", json={"name": "Duda 2", "email": "DUDA.LIMA@teste.com", "password": "x12345"}).status_code == 409


def test_handle_nao_repete(client):
    a = client.post("/auth/register", json={"name": "Jo A", "email": "jo@a.com", "password": "senha123"}).json()["user"]["handle"]
    b = client.post("/auth/register", json={"name": "Jo B", "email": "jo@b.com", "password": "senha123"}).json()["user"]["handle"]
    assert a != b and len(a) >= 3 and len(b) >= 3


def test_conta_google_tentando_senha(client):
    client.post("/auth/social", json={"provider": "google", "name": "Gi", "email": "gi@gmail.com"})
    r = client.post("/auth/login", json={"email": "gi@gmail.com", "password": "qualquer"})
    assert r.status_code == 400 and "Google" in r.json()["detail"]


def test_nome_obrigatorio(client):
    r = client.post("/auth/register", json={"name": "  ", "email": "semnome@teste.com", "password": "senha123"})
    assert r.status_code == 422


# ---------- Esqueci a senha ----------
import pytest  # noqa: E402

from app.routers import auth as auth_router  # noqa: E402


@pytest.fixture
def emails(monkeypatch):
    """Troca o envio real por uma lista: cada item é (para, nome, link)."""
    enviados = []
    monkeypatch.setattr(auth_router, "send_password_reset", lambda to, name, link: enviados.append((to, name, link)))
    auth_router._last_reset_email.clear()
    return enviados


def _token_do_link(link: str) -> str:
    assert "/redefinir-senha.html#token=" in link
    return link.split("#token=", 1)[1]


def test_esqueci_senha_envia_link_e_troca_senha(client, emails):
    client.post("/auth/register", json={"name": "Eva Lima", "email": "eva@teste.com", "password": "antiga123"})

    r = client.post("/auth/forgot-password", json={"email": "EVA@teste.com"})
    assert r.status_code == 202
    assert len(emails) == 1 and emails[0][0] == "eva@teste.com"
    token = _token_do_link(emails[0][2])

    r = client.post("/auth/reset-password", json={"token": token, "new_password": "nova12345"})
    assert r.status_code == 200 and r.json()["user"]["email"] == "eva@teste.com"
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).status_code == 200

    assert client.post("/auth/login", json={"email": "eva@teste.com", "password": "antiga123"}).status_code == 401
    assert client.post("/auth/login", json={"email": "eva@teste.com", "password": "nova12345"}).status_code == 200


def test_link_de_redefinicao_so_vale_uma_vez(client, emails):
    client.post("/auth/register", json={"name": "Fê", "email": "fe@teste.com", "password": "antiga123"})
    client.post("/auth/forgot-password", json={"email": "fe@teste.com"})
    token = _token_do_link(emails[0][2])

    assert client.post("/auth/reset-password", json={"token": token, "new_password": "nova12345"}).status_code == 200
    r = client.post("/auth/reset-password", json={"token": token, "new_password": "outra123"})
    assert r.status_code == 400


def test_esqueci_senha_nao_revela_se_email_existe(client, emails):
    client.post("/auth/social", json={"provider": "google", "name": "Gu", "email": "gu@gmail.com"})
    sem_conta = client.post("/auth/forgot-password", json={"email": "ninguem@teste.com"})
    conta_google = client.post("/auth/forgot-password", json={"email": "gu@gmail.com"})
    assert sem_conta.status_code == conta_google.status_code == 202
    assert sem_conta.json() == conta_google.json()
    assert emails == []  # nenhuma das duas tem senha para redefinir


def test_esqueci_senha_espera_antes_de_reenviar(client, emails):
    client.post("/auth/register", json={"name": "Hugo", "email": "hugo@teste.com", "password": "antiga123"})
    client.post("/auth/forgot-password", json={"email": "hugo@teste.com"})
    client.post("/auth/forgot-password", json={"email": "hugo@teste.com"})
    assert len(emails) == 1


def test_token_de_redefinicao_nao_serve_para_entrar(client, emails):
    client.post("/auth/register", json={"name": "Iris", "email": "iris@teste.com", "password": "antiga123"})
    client.post("/auth/forgot-password", json={"email": "iris@teste.com"})
    token = _token_do_link(emails[0][2])
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_invalido(client):
    r = client.post("/auth/reset-password", json={"token": "isso-nao-e-um-token", "new_password": "nova12345"})
    assert r.status_code == 400
