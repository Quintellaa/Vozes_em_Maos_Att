"""Hash de senha e criação/verificação de tokens JWT."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Retorna o user_id do token, ou None se o token for inválido/expirado."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose"):  # token de redefinição de senha não serve para entrar no app
            return None
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


# ---------- Redefinição de senha ("Esqueci a senha") ----------
# O link do e-mail leva um código curto e aleatório (16 caracteres). No banco fica só o
# hash dele: quem vê o banco não consegue montar um link válido.


def new_password_reset_code() -> tuple[str, str]:
    """Gera (código que vai no link, hash que fica no banco)."""
    code = secrets.token_urlsafe(12)  # 16 caracteres, 96 bits aleatórios
    return code, hash_password_reset_code(code)


def hash_password_reset_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()
