"""Envio de e-mails (por enquanto, só o de redefinição de senha).

Escolhe o jeito de enviar pelo que estiver no .env:
  1. BREVO_API_KEY  → API da Brevo por HTTPS (funciona no plano grátis do Render);
  2. SMTP_HOST      → servidor SMTP (ex.: Gmail com senha de app);
  3. nenhum         → não envia: escreve o e-mail no terminal do backend (modo de teste).
"""
import json
import logging
import smtplib
import urllib.request
from email.message import EmailMessage
from html import escape

from app.config import settings

log = logging.getLogger("vozes.mailer")


def _send_brevo(to: str, subject: str, text: str, html: str) -> None:
    body = {
        "sender": {"name": settings.mail_from_name, "email": settings.mail_from},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": text,
        "htmlContent": html,
    }
    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(body).encode(),
        headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


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
    """Envia um e-mail. Roda em segundo plano (BackgroundTasks), então só registra erros no log."""
    try:
        if settings.brevo_api_key:
            _send_brevo(to, subject, text, html)
        elif settings.smtp_host:
            _send_smtp(to, subject, text, html)
        else:
            # print, e não log: aparece no terminal do uvicorn sem configurar nada.
            print(f"\n[E-MAIL NÃO ENVIADO — configure BREVO_API_KEY ou SMTP_HOST no .env]\nPara: {to}\nAssunto: {subject}\n\n{text}\n", flush=True)
    except Exception:
        log.exception("Falha ao enviar e-mail para %s", to)


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
