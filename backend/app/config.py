"""Configurações centrais da aplicação, lidas de variáveis de ambiente (.env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Banco de dados — SQLite por padrão (arquivo local, sem precisar instalar nada).
    # Para usar PostgreSQL de novo no futuro (ex.: com Docker), troque no .env:
    # DATABASE_URL=postgresql://sinaliza:sinaliza@db:5432/sinaliza
    database_url: str = "sqlite:///./sinaliza.db"

    # JWT
    jwt_secret_key: str = "changeme-generate-a-real-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 dias

    # CORS — em produção, restrinja para o domínio real do front-end.
    cors_origins: list[str] = ["http://localhost:5500", "http://127.0.0.1:5500"]

    # OAuth (usados apenas quando a verificação real de token for implementada — ver auth.py)
    google_client_id: str = ""
    apple_client_id: str = ""

    # ---- E-mail ("Esqueci a senha") ----
    # Por quanto tempo o link de redefinição vale.
    password_reset_expire_minutes: int = 30
    # Endereço do site usado no link do e-mail (ex.: https://vozes-em-maos.onrender.com).
    # Vazio = o mesmo endereço por onde a pessoa pediu o link.
    app_url: str = ""
    # Remetente que aparece no e-mail. Precisa ser um endereço liberado no serviço de envio.
    mail_from: str = ""
    mail_from_name: str = "Vozes em Mãos"
    # Opção 1 — Gmail por um Google Apps Script (tools/email-gmail/Codigo.gs).
    # Funciona no plano grátis do Render, que bloqueia as portas de SMTP. Passo a passo em COMO-CONFIGURAR-EMAIL.md.
    gmail_script_url: str = ""     # endereço do script implantado, terminando em /exec
    gmail_script_secret: str = ""  # o mesmo valor de SEGREDO no script
    # Opção 2 — Mailjet (API por HTTPS, plano grátis de 200 e-mails/dia). Também funciona no Render.
    mailjet_api_key: str = ""
    mailjet_secret_key: str = ""
    # Opção 3 — Brevo (API por HTTPS, plano grátis de 300 e-mails/dia). Também funciona no Render.
    brevo_api_key: str = ""
    # Opção 4 — SMTP (ex.: Gmail com "senha de app": smtp.gmail.com, porta 587). Só fora do Render grátis.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # Nenhuma configurada: o link aparece no terminal do backend (bom para testar).

    # Modelo de reconhecimento de Libras (gerado por tools/train_and_export.py).
    # Se o arquivo não existir, a API sobe normalmente e só a rota de
    # reconhecimento responde 503 — o resto do app continua funcionando.
    model_path: str = "models/libras_pose_hands.joblib"
    min_confidence: float = 0.25  # abaixo disso, a API responde "não reconheci"

    # Pasta do front-end que o backend entrega em "/". Vazio = ../frontend (layout do repositório).
    # No Docker (Dockerfile da raiz) é /code/frontend.
    frontend_dir: str = ""

    # protected_namespaces=(): o Pydantic reserva o prefixo "model_" pra uso
    # interno e avisa sobre o nosso campo model_path. Como o campo é legítimo
    # (caminho do modelo de reconhecimento), desligamos esse aviso.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", protected_namespaces=()
    )


settings = Settings()
