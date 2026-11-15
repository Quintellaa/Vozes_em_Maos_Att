"""Envio de e-mails (por enquanto, só o de redefinição de senha).

Escolhe o jeito de enviar pelo que estiver no .env (o primeiro preenchido vale):
  1. GMAIL_SCRIPT_URL + GMAIL_SCRIPT_SECRET → seu Gmail, por um Google Apps Script
     (tools/email-gmail/Codigo.gs; funciona no plano grátis do Render);
  2. MAILJET_API_KEY + MAILJET_SECRET_KEY → API da Mailjet por HTTPS;
  3. BREVO_API_KEY  → API da Brevo por HTTPS;
  4. SMTP_HOST      → servidor SMTP (não funciona no plano grátis do Render);
  5. nenhum         → não envia: escreve o e-mail no terminal do backend (modo de teste).
"""
import base64
import json
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from html import escape

from app.config import settings


def _post_json(url: str, body: dict, headers: dict | None = None) -> bytes:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def _send_gmail_script(to: str, subject: str, text: str, html: str) -> None:
    # O Google responde com um redirecionamento; o urllib segue sozinho e devolve o JSON do script.
    raw = _post_json(settings.gmail_script_url, {
        "secret": settings.gmail_script_secret,
        "to": to,
        "subject": subject,
        "text": text,
        "html": html,
        "name": settings.mail_from_name,
    })
    try:
        answer = json.loads(raw)
    except ValueError:
        # Veio uma página do Google em vez de JSON: quase sempre o script não foi implantado
        # com "Quem pode acessar: Qualquer pessoa", ou o endereço não termina em /exec.
        raise RuntimeError(
            "o script do Gmail não respondeu como esperado. Confira se GMAIL_SCRIPT_URL termina em /exec "
            "e se a implantação está com 'Quem pode acessar: Qualquer pessoa'."
        )
    if not answer.get("ok"):
        raise RuntimeError(f"o script do Gmail recusou: {answer.get('error')}")


def _send_mailjet(to: str, subject: str, text: str, html: str) -> None:
    body = {
        "Messages": [{
            "From": {"Email": settings.mail_from, "Name": settings.mail_from_name},
            "To": [{"Email": to}],
            "Subject": subject,
            "TextPart": text,
            "HTMLPart": html,
        }]
    }
    # A Mailjet usa as duas chaves como usuário e senha (autenticação "Basic").
    credentials = base64.b64encode(f"{settings.mailjet_api_key}:{settings.mailjet_secret_key}".encode()).decode()
    _post_json("https://api.mailjet.com/v3.1/send", body, {"Authorization": f"Basic {credentials}"})


def _send_brevo(to: str, subject: str, text: str, html: str) -> None:
    body = {
        "sender": {"name": settings.mail_from_name, "email": settings.mail_from},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": text,
        "htmlContent": html,
    }
    _post_json("https://api.brevo.com/v3/smtp/email", body, {"api-key": settings.brevo_api_key})


def _send_smtp(to: str, subject: str, text: str, html: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.mail_from_name} <{settings.mail_from or settings.smtp_user}>"
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    if settings.smtp_port == 465:  # SSL direto
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    else:  # 587: conexão normal que vira segura com STARTTLS
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)


def send_email(to: str, subject: str, text: str, html: str) -> None:
    """Envia um e-mail. Roda em segundo plano (BackgroundTasks), então só escreve erros no log.
    (print, e não logging: aparece no terminal do uvicorn e nos Logs do Render sem configurar nada.)"""
    try:
        if settings.gmail_script_url and settings.gmail_script_secret:
            _send_gmail_script(to, subject, text, html)
        elif settings.mailjet_api_key and settings.mailjet_secret_key:
            _send_mailjet(to, subject, text, html)
        elif settings.brevo_api_key:
            _send_brevo(to, subject, text, html)
        elif settings.smtp_host:
            _send_smtp(to, subject, text, html)
        else:
            print(f"\n[E-MAIL NÃO ENVIADO — configure GMAIL_SCRIPT_URL e GMAIL_SCRIPT_SECRET (ver COMO-CONFIGURAR-EMAIL.md)]\nPara: {to}\nAssunto: {subject}\n\n{text}\n", flush=True)
            return
        print(f"[E-MAIL ENVIADO] Para: {to} | Assunto: {subject}", flush=True)
    except urllib.error.HTTPError as err:
        # O serviço de envio explica o motivo no corpo da resposta (ex.: remetente não confirmado).
        detail = err.read().decode(errors="replace")[:500]
        print(f"[FALHA AO ENVIAR E-MAIL] Para: {to} | HTTP {err.code}: {detail}", flush=True)
    except Exception as err:
        print(f"[FALHA AO ENVIAR E-MAIL] Para: {to} | {type(err).__name__}: {err}", flush=True)


def password_reset_email(name: str, link: str, mascot_url: str) -> tuple[str, str, str]:
    """Monta (assunto, texto puro, HTML) do e-mail de "Esqueci a senha".

    O HTML segue o visual do app (azul #2563eb, cartão branco arredondado, fonte Inter) e
    usa tabelas e estilos inline, porque é o que o Gmail, o Outlook e o app de e-mail do
    celular entendem. O mascote vem do próprio site (img/mascote-email.png).
    """
    minutes = settings.password_reset_expire_minutes
    first_name = (name or "").split(" ")[0] or "Olá"
    subject = "Redefina sua senha do Vozes em Mãos"
    text = (
        f"Oi, {first_name}!\n\n"
        "Recebemos um pedido para redefinir a senha da sua conta no Vozes em Mãos.\n"
        f"Para criar uma senha nova, abra este link (vale por {minutes} minutos e só funciona uma vez):\n\n"
        f"{link}\n\n"
        "Não foi você? Pode ignorar este e-mail: sua senha continua a mesma.\n\n"
        "— Vozes em Mãos"
    )
    safe_link = escape(link, quote=True)
    safe_name = escape(first_name)
    safe_mascot = escape(mascot_url, quote=True)
    font = "Inter,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
    html = f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>{subject}</title></head>
<body style="margin:0;padding:0;background:#e8ecf3">
<!-- texto que aparece ao lado do assunto na caixa de entrada -->
<div style="display:none;max-height:0;overflow:hidden;opacity:0">Toque no botão para criar uma senha nova. O link vale por {minutes} minutos.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#e8ecf3" style="background:#e8ecf3">
<tr><td align="center" style="padding:28px 12px">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:480px;background:#ffffff;border-radius:24px;overflow:hidden;box-shadow:0 12px 32px -12px rgba(15,23,42,.18)">

    <!-- topo: mascote acenando sobre o azul clarinho do app -->
    <tr><td align="center" bgcolor="#dbeafe" style="background:#dbeafe;background-image:linear-gradient(180deg,#eff6ff 0%,#dbeafe 100%);padding:28px 24px 16px">
      <p style="margin:0 0 14px;font-family:{font};font-size:15px;font-weight:800;letter-spacing:-.01em;color:#2563eb">Vozes em Mãos</p>
      <img src="{safe_mascot}" width="120" height="171" alt="Mascote do Vozes em Mãos acenando" style="display:block;width:120px;height:auto;border:0;outline:none">
    </td></tr>

    <!-- conteúdo -->
    <tr><td style="padding:32px 32px 8px;font-family:{font};color:#0f172a">
      <h1 style="margin:0 0 12px;font-size:26px;line-height:1.2;font-weight:800;letter-spacing:-.02em;color:#0f172a">Esqueceu a senha, {safe_name}?</h1>
      <p style="margin:0 0 28px;font-size:15px;line-height:1.6;color:#64748b">Acontece com todo mundo! Toque no botão abaixo para criar uma senha nova e voltar a traduzir.</p>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr><td align="center" bgcolor="#2563eb" style="border-radius:16px;background:#2563eb;box-shadow:0 10px 20px -8px rgba(37,99,235,.6)">
          <a href="{safe_link}" style="display:block;padding:16px 24px;font-family:{font};font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:16px">Criar nova senha</a>
        </td></tr>
      </table>

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:20px">
        <tr><td bgcolor="#f8fafc" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px 14px;font-size:13px;line-height:1.5;color:#64748b">
          <strong style="color:#0f172a">Válido por {minutes} minutos</strong> e só funciona uma vez.
        </td></tr>
      </table>

      <p style="margin:20px 0 0;font-size:13px;line-height:1.6;color:#64748b">O botão não abriu? Copie este endereço no navegador:<br>
        <a href="{safe_link}" style="color:#2563eb;font-weight:600;text-decoration:none;word-break:break-all">{safe_link}</a></p>
    </td></tr>

    <!-- aviso de segurança -->
    <tr><td style="padding:20px 32px 28px;font-family:{font}">
      <p style="margin:0;padding-top:20px;border-top:1px solid #e2e8f0;font-size:13px;line-height:1.6;color:#64748b">
        <strong style="color:#0f172a">Não foi você?</strong> Pode ignorar este e-mail: sua senha continua a mesma.</p>
    </td></tr>
  </table>

  <p style="margin:20px 0 0;font-family:{font};font-size:12px;line-height:1.5;color:#94a3b8">Vozes em Mãos · Quebrando barreiras de comunicação com a Libras</p>
</td></tr>
</table>
</body>
</html>"""
    return subject, text, html


def send_password_reset(to: str, name: str, link: str, mascot_url: str) -> None:
    subject, text, html = password_reset_email(name, link, mascot_url)
    send_email(to, subject, text, html)
