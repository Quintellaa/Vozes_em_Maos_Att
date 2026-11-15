"""Testes do envio de e-mail — sem enviar nada de verdade (a chamada à internet é trocada por uma falsa)."""
import base64
import io
import json
import urllib.error

import pytest

from app import mailer
from app.config import settings


class _RespostaFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b"{}"


@pytest.fixture
def pedidos(monkeypatch):
    """Guarda cada chamada que o mailer faria à internet."""
    feitos = []

    def urlopen_falso(request, timeout=None):
        feitos.append(request)
        return _RespostaFalsa()

    monkeypatch.setattr(mailer.urllib.request, "urlopen", urlopen_falso)
    for campo in ("gmail_script_url", "gmail_script_secret", "mailjet_api_key", "mailjet_secret_key", "brevo_api_key", "smtp_host"):
        monkeypatch.setattr(settings, campo, "")
    monkeypatch.setattr(settings, "mail_from", "contato@vozes.com")
    return feitos


def _resposta_do_script(monkeypatch, pedidos, corpo: bytes):
    """Faz o urlopen falso devolver `corpo`, como se fosse a resposta do Google Apps Script."""
    class Resposta(_RespostaFalsa):
        def read(self):
            return corpo

    def urlopen_falso(request, timeout=None):
        pedidos.append(request)
        return Resposta()

    monkeypatch.setattr(mailer.urllib.request, "urlopen", urlopen_falso)
    monkeypatch.setattr(settings, "gmail_script_url", "https://script.google.com/macros/s/ABC/exec")
    monkeypatch.setattr(settings, "gmail_script_secret", "meu-segredo")


def test_gmail_script_monta_o_pedido_certo(pedidos, monkeypatch, capsys):
    _resposta_do_script(monkeypatch, pedidos, b'{"ok": true, "restantesHoje": 99}')
    monkeypatch.setattr(settings, "mailjet_api_key", "chave")  # mesmo com Mailjet configurada, o Gmail vem primeiro
    monkeypatch.setattr(settings, "mailjet_secret_key", "segredo")

    mailer.send_password_reset("ana@teste.com", "Ana Souza", "https://app/redefinir-senha.html#token=abc")

    assert len(pedidos) == 1
    assert pedidos[0].full_url == "https://script.google.com/macros/s/ABC/exec"
    corpo = json.loads(pedidos[0].data)
    assert corpo["secret"] == "meu-segredo" and corpo["to"] == "ana@teste.com"
    assert "#token=abc" in corpo["text"] and "#token=abc" in corpo["html"]
    assert "[E-MAIL ENVIADO]" in capsys.readouterr().out


def test_gmail_script_recusou_aparece_no_log(pedidos, monkeypatch, capsys):
    _resposta_do_script(monkeypatch, pedidos, b'{"ok": false, "error": "Segredo incorreto"}')
    mailer.send_email("ana@teste.com", "Oi", "texto", "<p>html</p>")
    saida = capsys.readouterr().out
    assert "[FALHA AO ENVIAR E-MAIL]" in saida and "Segredo incorreto" in saida


def test_gmail_script_mal_implantado_explica_o_que_conferir(pedidos, monkeypatch, capsys):
    # Implantação sem "Qualquer pessoa": o Google devolve uma página de login em HTML.
    _resposta_do_script(monkeypatch, pedidos, b"<!DOCTYPE html><html>Fazer login</html>")
    mailer.send_email("ana@teste.com", "Oi", "texto", "<p>html</p>")
    saida = capsys.readouterr().out
    assert "[FALHA AO ENVIAR E-MAIL]" in saida and "/exec" in saida and "Qualquer pessoa" in saida


def test_mailjet_monta_o_pedido_certo(pedidos, monkeypatch, capsys):
    monkeypatch.setattr(settings, "mailjet_api_key", "chave")
    monkeypatch.setattr(settings, "mailjet_secret_key", "segredo")

    mailer.send_password_reset("ana@teste.com", "Ana Souza", "https://app/redefinir-senha.html#token=abc")

    assert len(pedidos) == 1
    req = pedidos[0]
    assert req.full_url == "https://api.mailjet.com/v3.1/send"
    assert req.get_header("Authorization") == "Basic " + base64.b64encode(b"chave:segredo").decode()
    msg = json.loads(req.data)["Messages"][0]
    assert msg["From"]["Email"] == "contato@vozes.com"
    assert msg["To"] == [{"Email": "ana@teste.com"}]
    assert "#token=abc" in msg["TextPart"] and "#token=abc" in msg["HTMLPart"]
    assert "[E-MAIL ENVIADO]" in capsys.readouterr().out


def test_mailjet_tem_prioridade_sobre_brevo(pedidos, monkeypatch):
    monkeypatch.setattr(settings, "mailjet_api_key", "chave")
    monkeypatch.setattr(settings, "mailjet_secret_key", "segredo")
    monkeypatch.setattr(settings, "brevo_api_key", "outra")
    mailer.send_email("ana@teste.com", "Oi", "texto", "<p>html</p>")
    assert "mailjet" in pedidos[0].full_url


def test_sem_configuracao_mostra_o_link_no_terminal(pedidos, capsys):
    mailer.send_password_reset("ana@teste.com", "Ana", "https://app/redefinir-senha.html#token=abc")
    assert pedidos == []
    assert "#token=abc" in capsys.readouterr().out


def test_erro_do_servico_aparece_no_log_sem_derrubar_o_app(monkeypatch, capsys):
    def urlopen_com_erro(request, timeout=None):
        corpo = io.BytesIO(b'{"ErrorMessage":"sender not validated"}')
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, corpo)

    monkeypatch.setattr(mailer.urllib.request, "urlopen", urlopen_com_erro)
    monkeypatch.setattr(settings, "mailjet_api_key", "chave")
    monkeypatch.setattr(settings, "mailjet_secret_key", "errada")

    mailer.send_email("ana@teste.com", "Oi", "texto", "<p>html</p>")  # não pode levantar exceção

    saida = capsys.readouterr().out
    assert "[FALHA AO ENVIAR E-MAIL]" in saida and "HTTP 401" in saida and "sender not validated" in saida
