"""Configurações centrais da aplicação, lidas de variáveis de ambiente (.env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Banco de dados
    database_url: str = "postgresql://sinaliza:sinaliza@localhost:5432/sinaliza"

    # JWT
    jwt_secret_key: str = "changeme-generate-a-real-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 dias

    # CORS — em produção, restrinja para o domínio real do front-end.
    cors_origins: list[str] = ["http://localhost:5500", "http://127.0.0.1:5500"]

    # OAuth (usados apenas quando a verificação real de token for implementada — ver auth.py)
    google_client_id: str = ""
    apple_client_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
