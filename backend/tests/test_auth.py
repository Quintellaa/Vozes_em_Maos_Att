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
