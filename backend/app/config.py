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

    # Modelo de reconhecimento de Libras (gerado por tools/train_and_export.py).
    # Se o arquivo não existir, a API sobe normalmente e só a rota de
    # reconhecimento responde 503 — o resto do app continua funcionando.
    model_path: str = "models/libras_svm.joblib"
    min_confidence: float = 0.25  # abaixo disso, a API responde "não reconheci"

    # protected_namespaces=(): o Pydantic reserva o prefixo "model_" pra uso
    # interno e avisa sobre o nosso campo model_path. Como o campo é legítimo
    # (caminho do modelo de reconhecimento), desligamos esse aviso.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", protected_namespaces=()
    )


settings = Settings()
