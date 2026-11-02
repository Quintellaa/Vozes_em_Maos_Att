"""Testes de comunidades: listar, entrar/sair, criar e posts."""
import uuid


def _usuario(client, nome="Membro Teste"):
    email = f"c_{uuid.uuid4().hex[:8]}@teste.com"
    r = client.post("/auth/register", json={"name": nome, "email": email, "password": "senha123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_comunidades_iniciais_existem(client):
    h = _usuario(client)
    nomes = [c["name"] for c in client.get("/communities", headers=h).json()]
    assert "Libras na Facu" in nomes and "Saúde Inclusiva" in nomes
    # busca ignora acentos e maiúsculas
    achadas = [c["name"] for c in client.get("/communities", params={"search": "SAUDE"}, headers=h).json()]
    assert "Saúde Inclusiva" in achadas


def test_entrar_sair_e_filtro_minhas(client):
    h = _usuario(client)
    cid = client.get("/communities", headers=h).json()[0]["id"]
    antes = client.get(f"/communities/{cid}", headers=h).json()["member_count"]

    r = client.post(f"/communities/{cid}/join", headers=h)
    assert r.json()["joined"] is True and r.json()["member_count"] == antes + 1
    client.post(f"/communities/{cid}/join", headers=h)  # entrar 2x não duplica
    assert client.get(f"/communities/{cid}", headers=h).json()["member_count"] == antes + 1
    assert [c["id"] for c in client.get("/communities?joined=true", headers=h).json()] == [cid]

    r = client.delete(f"/communities/{cid}/join", headers=h)
    assert r.json()["joined"] is False and r.json()["member_count"] == antes
    assert client.get("/communities?joined=true", headers=h).json() == []


def test_criar_comunidade_e_busca(client):
    h = _usuario(client)
    nome = f"Teatro em Libras {uuid.uuid4().hex[:4]}"
    r = client.post("/communities", json={"name": nome, "description": "Peças", "category": "cultura", "icon": "hand", "color": "pink"}, headers=h)
    assert r.status_code == 201
    c = r.json()
    assert c["joined"] and c["is_owner"] and c["member_count"] == 1
    assert client.post("/communities", json={"name": nome.upper()}, headers=h).status_code == 409
    achadas = client.get("/communities", params={"search": nome.split()[-1]}, headers=h).json()
    assert [x["id"] for x in achadas] == [c["id"]]
    assert all(x["category"] == "cultura" for x in client.get("/communities?category=cultura", headers=h).json())


def test_posts_so_para_membros_e_apagar(client):
    dono, outro = _usuario(client, "Dono"), _usuario(client, "Outro")
    cid = client.get("/communities", headers=dono).json()[0]["id"]

    assert client.post(f"/communities/{cid}/posts", json={"text": "oi"}, headers=outro).status_code == 403
    client.post(f"/communities/{cid}/join", headers=outro)
    r = client.post(f"/communities/{cid}/posts", json={"text": "  Olá, pessoal!  "}, headers=outro)
    assert r.status_code == 201 and r.json()["text"] == "Olá, pessoal!" and r.json()["mine"]
    assert r.json()["created_at"].endswith(("Z", "+00:00"))  # data com fuso, para o front converter certo
    pid = r.json()["id"]

    posts = client.get(f"/communities/{cid}/posts", headers=dono).json()
    assert posts[0]["author"]["name"] == "Outro" and posts[0]["mine"] is False
    assert client.delete(f"/communities/{cid}/posts/{pid}", headers=dono).status_code == 403
    assert client.delete(f"/communities/{cid}/posts/{pid}", headers=outro).status_code == 204
