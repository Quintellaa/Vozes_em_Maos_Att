"""Testes do histórico de traduções."""


def test_criar_listar_filtrar(client, auth_headers):
    client.post("/history", json={"type": "t", "text": "maçã"}, headers=auth_headers)
    client.post("/history", json={"type": "l", "text": "BANHEIRO"}, headers=auth_headers)

    todos = client.get("/history", headers=auth_headers).json()
    assert len(todos) == 2
    assert todos[0]["text"] == "BANHEIRO"  # mais recente primeiro

    so_libras = client.get("/history?type=l", headers=auth_headers).json()
    assert [h["text"] for h in so_libras] == ["BANHEIRO"]

    busca = client.get("/history?search=ma", headers=auth_headers).json()
    assert [h["text"] for h in busca] == ["maçã"]


def test_favoritar_e_apagar(client, auth_headers):
    entry = client.post("/history", json={"type": "t", "text": "cinco"}, headers=auth_headers).json()

    r = client.patch(f"/history/{entry['id']}/favorite", headers=auth_headers)
    assert r.json()["favorite"] is True
    assert len(client.get("/history?favorite=true", headers=auth_headers).json()) == 1

    assert client.delete(f"/history/{entry['id']}", headers=auth_headers).status_code == 204
    assert client.get("/history", headers=auth_headers).json() == []


def test_usuario_nao_ve_historico_de_outro(client, auth_headers):
    """Segurança: um usuário não pode ler nem apagar registros de outro."""
    entry = client.post("/history", json={"type": "t", "text": "segredo"}, headers=auth_headers).json()

    r = client.post("/auth/register", json={"name": "Outro", "email": "outro@teste.com", "password": "123456"})
    outro = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert client.get("/history", headers=outro).json() == []
    assert client.delete(f"/history/{entry['id']}", headers=outro).status_code == 404
    assert client.patch(f"/history/{entry['id']}/favorite", headers=outro).status_code == 404


def test_limpar_tudo(client, auth_headers):
    for palavra in ["um", "dois", "três"]:
        client.post("/history", json={"type": "t", "text": palavra}, headers=auth_headers)
    assert client.delete("/history", headers=auth_headers).status_code == 204
    assert client.get("/history", headers=auth_headers).json() == []
