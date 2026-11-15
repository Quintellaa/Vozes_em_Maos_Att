"""Envio de e-mails (por enquanto, só o de redefinição de senha).

Escolhe o jeito de enviar pelo que estiver no .env (o primeiro preenchido vale):
  1. MAILJET_API_KEY + MAILJET_SECRET_KEY → API da Mailjet por HTTPS (funciona no plano grátis do Render);
  2. BREVO_API_KEY  → API da Brevo por HTTPS (também funciona no Render);
  3. SMTP_HOST      → servidor SMTP (ex.: Gmail com senha de app);
  4. nenhum         → não envia: escreve o e-mail no terminal do backend (modo de teste).
"""
import base64
import json
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from html import escape

from app.config import settings


def _post_json(url: str, body: dict, headers: dict) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


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
        if settings.mailjet_api_key and settings.mailjet_secret_key:
            _send_mailjet(to, subject, text, html)
        elif settings.brevo_api_key:
            _send_brevo(to, subject, text, html)
        elif settings.smtp_host:
            _send_smtp(to, subject, text, html)
        else:
            print(f"\n[E-MAIL NÃO ENVIADO — configure MAILJET_API_KEY e MAILJET_SECRET_KEY no .env]\nPara: {to}\nAssunto: {subject}\n\n{text}\n", flush=True)
            return
        print(f"[E-MAIL ENVIADO] Para: {to} | Assunto: {subject}", flush=True)
    except urllib.error.HTTPError as err:
        # O serviço de envio explica o motivo no corpo da resposta (ex.: remetente não confirmado).
        detail = err.read().decode(errors="replace")[:500]
        print(f"[FALHA AO ENVIAR E-MAIL] Para: {to} | HTTP {err.code}: {detail}", flush=True)
    except Exception as err:
        print(f"[FALHA AO ENVIAR E-MAIL] Para: {to} | {type(err).__name__}: {err}", flush=True)


def send_password_reset(to: str, name: str, link: str) -> None:
    minutes = settings.password_reset_expire_minutes
    first_name = (name or "").split(" ")[0] or "Olá"
    subject = "Redefina sua senha do Vozes em Mãos"
    text = (
        f"{first_name}, recebemos um pedido para redefinir a senha da sua conta no Vozes em Mãos.\n\n"
        f"Para criar uma senha nova, abra este link (vale por {minutes} minutos e só pode ser usado uma vez):\n"
        f"{link}\n\n"
        "Se não foi você que pediu, ignore este e-mail: sua senha continua a mesma."
    )
    safe_link = escape(link, quote=True)
    html = f"""\
<div style="font-family:Inter,Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#0f172a">
  <h2 style="margin:0 0 12px;color:#2563eb">Vozes em Mãos</h2>
  <p>{escape(first_name)}, recebemos um pedido para redefinir a senha da sua conta.</p>
  <p style="margin:24px 0">
    <a href="{safe_link}" style="background:#2563eb;color:#fff;padding:14px 22px;border-radius:12px;text-decoration:none;font-weight:700;display:inline-block">Criar nova senha</a>
  </p>
  <p style="font-size:13px;color:#64748b">O link vale por {minutes} minutos e só pode ser usado uma vez.
  Se o botão não funcionar, copie e cole este endereço no navegador:<br><a href="{safe_link}" style="color:#2563eb;word-break:break-all">{safe_link}</a></p>
  <p style="font-size:13px;color:#64748b">Se não foi você que pediu, ignore este e-mail: sua senha continua a mesma.</p>
</div>"""
    send_email(to, subject, text, html)
