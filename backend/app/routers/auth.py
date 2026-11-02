"""Rotas de autenticação."""
import base64
import binascii
import re
import time
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import AuthProvider, TranslationHistory, User
from app.schemas import AvatarUpload, PasswordChange, UserStats, SocialLogin, Token, UserLogin, UserOut, UserRegister, UserUpdate
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _find_by_email(db: Session, email: str) -> User | None:
    """E-mail não diferencia maiúsculas: "Ana@Gmail.com" e "ana@gmail.com" são a mesma conta."""
    return db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()


def _unique_handle(db: Session, email: str) -> str:
    """@usuário a partir do e-mail (só a-z, 0-9, ponto e _), sem repetir o de outra pessoa."""
    base = unicodedata.normalize("NFD", email.split("@")[0]).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9._]", "", base).strip("._")[:16] or "usuario"
    if len(base) < 3:
        base = (base + "usuario")[:7]
    handle, n = base, 1
    while db.query(User).filter(User.handle == handle).first():
        n += 1
        handle = f"{base}{n}"
    return handle


def _issue_token(user: User) -> Token:
    return Token(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if _find_by_email(db, payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já tem uma conta. Entre com ele.")

    user = User(
        name=payload.name,
        handle=_unique_handle(db, payload.email),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        auth_provider=AuthProvider.local,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = _find_by_email(db, payload.email)
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")

    if not user:
        raise invalid
    if not user.password_hash:
        # Conta criada pelo Google/Apple: não tem senha no Sinaliza.
        provider = getattr(user.auth_provider, "value", user.auth_provider)
        nome = {"google": "Google", "apple": "Apple"}.get(provider, "Google ou Apple")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Essa conta entra pelo {nome}. Use o botão “Entrar com {nome}”.")
    if not verify_password(payload.password, user.password_hash):
        raise invalid

    return _issue_token(user)


@router.post("/social", response_model=Token)
def social_login(payload: SocialLogin, db: Session = Depends(get_db)):
    """MOCK: aceita nome/e-mail enviados pelo cliente, igual ao mock atual do front-end
    (apple.html / google.html). Isso permite integrar o front-end sem bloquear o
    desenvolvimento do restante do backend.

    TODO antes de produção: verificar a autenticidade do token no backend em vez de
    confiar no nome/e-mail do body:
      - Google: validar o `id_token` recebido do Google Identity Services com a lib
        `google-auth` (google.oauth2.id_token.verify_oauth2_token), usando settings.google_client_id.
      - Apple: validar o `identity_token` (JWT assinado pela Apple) contra as chaves
        públicas JWKS da Apple, usando settings.apple_client_id como audience.
    Só depois de validar o token é seguro extrair nome/e-mail dele — nunca do body direto.
    """
    user = _find_by_email(db, payload.email)
    if not user:
        user = User(
            name=payload.name,
            handle=_unique_handle(db, payload.email),
            email=payload.email.lower(),
            password_hash=None,
            auth_provider=AuthProvider(payload.provider),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return _issue_token(user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza nome e/ou @usuário do perfil."""
    if payload.handle is not None and payload.handle != current_user.handle:
        taken = db.query(User).filter(User.handle == payload.handle, User.id != current_user.id).first()
        if taken:
            raise HTTPException(status.HTTP_409_CONFLICT, "Esse nome de usuário já está em uso.")
        current_user.handle = payload.handle
    if payload.name is not None:
        current_user.name = payload.name

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Troca a senha de contas de e-mail. Contas Google/Apple não têm senha no Sinaliza."""
    if not current_user.password_hash:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Sua conta entra pelo Google/Apple, então não tem senha no Sinaliza.",
        )
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A senha atual está incorreta.")
    if payload.current_password == payload.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A nova senha precisa ser diferente da atual.")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()


AVATAR_MAX_BYTES = 400 * 1024  # a foto recortada pelo front tem ~20–40 KB
AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.put("/me/avatar", response_model=UserOut)
def upload_avatar(
    payload: AvatarUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Salva a foto de perfil (enviada como data URL base64)."""
    header, _, encoded = payload.image.partition(",")
    media_type = header.removeprefix("data:").removesuffix(";base64")
    if not header.startswith("data:") or not header.endswith(";base64") or media_type not in AVATAR_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Envie uma imagem JPG, PNG ou WebP.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Imagem inválida.")
    if not data or len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Imagem muito grande (máx. 400 KB).")

    current_user.avatar = data
    current_user.avatar_type = media_type
    current_user.avatar_updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me/avatar", response_model=UserOut)
def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.avatar = None
    current_user.avatar_type = None
    current_user.avatar_updated_at = None
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/stats", response_model=UserStats)
def my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Números do cartão do perfil. Conta nova começa com tudo em 0."""
    translations = db.query(TranslationHistory).filter(TranslationHistory.user_id == current_user.id).count()
    # TODO: quando existirem aulas e selos no app, contar aqui a partir das tabelas deles.
    return UserStats(translations=translations, lessons=0, badges=0)
