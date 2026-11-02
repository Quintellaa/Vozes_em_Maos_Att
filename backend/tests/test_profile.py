"""Testes de edição de perfil e troca de senha."""
import uuid


def _novo_usuario(client, senha="senha123"):
    email = f"p_{uuid.uuid4().hex[:8]}@teste.com"
    r = client.post("/auth/register", json={"name": "Perfil Teste", "email": email, "password": senha})
    assert r.status_code == 201
    return email, {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_me_informa_provider(client):
    _, h = _novo_usuario(client)
    assert client.get("/auth/me", headers=h).json()["provider"] == "local"


def test_editar_nome_e_handle(client):
    _, h = _novo_usuario(client)
    handle = f"novo.{uuid.uuid4().hex[:6]}"
    r = client.patch("/auth/me", json={"name": "  Jean   Carlos ", "handle": handle}, headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Jean Carlos"
    assert r.json()["handle"] == handle
    assert client.get("/auth/me", headers=h).json()["handle"] == handle


def test_handle_invalido_ou_repetido(client):
    _, h1 = _novo_usuario(client)
    _, h2 = _novo_usuario(client)
    assert client.patch("/auth/me", json={"handle": "Com Espaço"}, headers=h1).status_code == 422
    handle = f"unico_{uuid.uuid4().hex[:6]}"
    assert client.patch("/auth/me", json={"handle": handle}, headers=h1).status_code == 200
    assert client.patch("/auth/me", json={"handle": handle}, headers=h2).status_code == 409


def test_trocar_senha(client):
    email, h = _novo_usuario(client, "antiga1")
    r = client.post("/auth/password", json={"current_password": "errada", "new_password": "nova123"}, headers=h)
    assert r.status_code == 400
    r = client.post("/auth/password", json={"current_password": "antiga1", "new_password": "nova123"}, headers=h)
    assert r.status_code == 204
    assert client.post("/auth/login", json={"email": email, "password": "antiga1"}).status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": "nova123"}).status_code == 200


def test_conta_social_nao_tem_senha(client):
    email = f"s_{uuid.uuid4().hex[:8]}@gmail.com"
    r = client.post("/auth/social", json={"provider": "google", "name": "Social", "email": email})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert r.json()["user"]["provider"] == "google"
    r = client.post("/auth/password", json={"current_password": "x", "new_password": "nova123"}, headers=h)
    assert r.status_code == 400


FOTO_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAAEUlEQVR42mP8z8DwnwEIGBkACRgD/6Oc0bYAAAAASUVORK5CYII="
)


def test_foto_de_perfil_aparece_nos_posts(client):
    _, h = _novo_usuario(client)
    assert client.get("/auth/me", headers=h).json()["avatar_url"] is None

    r = client.put("/auth/me/avatar", json={"image": FOTO_PNG}, headers=h)
    assert r.status_code == 200
    url = r.json()["avatar_url"]
    assert url.startswith("/users/") and "?v=" in url

    img = client.get(url)  # pública: o <img> não manda token
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"

    cid = client.get("/communities", headers=h).json()[0]["id"]
    client.post(f"/communities/{cid}/join", headers=h)
    client.post(f"/communities/{cid}/posts", json={"text": "com foto"}, headers=h)
    assert client.get(f"/communities/{cid}/posts", headers=h).json()[0]["author"]["avatar_url"] == url

    r = client.delete("/auth/me/avatar", headers=h)
    assert r.json()["avatar_url"] is None
    assert client.get(url).status_code == 404


def test_foto_invalida(client):
    _, h = _novo_usuario(client)
    assert client.put("/auth/me/avatar", json={"image": "data:text/html;base64,PGI+"}, headers=h).status_code == 400
    assert client.put("/auth/me/avatar", json={"image": "data:image/png;base64,@@@"}, headers=h).status_code == 400


def test_estatisticas_comecam_zeradas_e_contam_traducoes(client):
    _, h = _novo_usuario(client)
    assert client.get("/auth/me/stats", headers=h).json() == {"translations": 0, "lessons": 0, "badges": 0}
    client.post("/history", json={"type": "t", "text": "olá"}, headers=h)
    client.post("/history", json={"type": "l", "text": "obrigado"}, headers=h)
    assert client.get("/auth/me/stats", headers=h).json()["translations"] == 2
