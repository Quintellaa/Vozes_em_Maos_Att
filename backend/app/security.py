"""Hash de senha e criação/verificação de tokens JWT."""
import hashlib
import hmac
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
RESET_PURPOSE = "password_reset"


def _password_fingerprint(password_hash: str) -> str:
    """Pedacinho do hash da senha atual. Entra no token de redefinição: quando a senha muda,
    o token deixa de bater — por isso cada link só funciona uma vez, sem precisar de tabela nova."""
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def create_password_reset_token(user_id: int, password_hash: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "purpose": RESET_PURPOSE, "pwd": _password_fingerprint(password_hash)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def read_password_reset_token(token: str) -> tuple[int, str] | None:
    """Retorna (user_id, marca da senha) do link, ou None se for inválido/expirado."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != RESET_PURPOSE:
            return None
        return int(payload["sub"]), str(payload["pwd"])
    except (JWTError, KeyError, ValueError):
        return None


def password_reset_token_matches(fingerprint: str, password_hash: str | None) -> bool:
    return bool(password_hash) and hmac.compare_digest(fingerprint, _password_fingerprint(password_hash))
