"""Rotas de autenticação."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import AuthProvider, User
from app.schemas import SocialLogin, Token, UserLogin, UserOut, UserRegister
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _handle_from_email(email: str) -> str:
    return email.split("@")[0]


def _issue_token(user: User) -> Token:
    return Token(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já está cadastrado.")

    user = User(
        name=payload.name,
        handle=_handle_from_email(payload.email),
        email=payload.email,
        password_hash=hash_password(payload.password),
        auth_provider=AuthProvider.local,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos.")

    if not user or not user.password_hash:
        raise invalid
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
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        user = User(
            name=payload.name,
            handle=_handle_from_email(payload.email),
            email=payload.email,
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
