"""Schemas Pydantic — contratos de entrada/saída da API (independentes dos modelos de DB)."""
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


def avatar_url_for(user) -> Optional[str]:
    """URL pública da foto de um usuário (objeto do banco), ou None se ele não tiver foto."""
    version = getattr(user, "avatar_updated_at", None)
    if not version or not getattr(user, "id", None):
        return None
    return f"/users/{user.id}/avatar?v={version}"


# ---------- Auth ----------
class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class SocialLogin(BaseModel):
    """MOCK: hoje aceita nome/e-mail direto do cliente (como o front-end mock atual envia).
    Antes de produção, troque por verificação real do id_token do Google / identity_token da Apple
    (ver TODO em routers/auth.py) e pare de confiar em nome/e-mail vindos do body.
    """
    provider: Literal["google", "apple"]
    name: str
    email: EmailStr


class UserOut(BaseModel):
    id: int
    name: str
    handle: str
    email: EmailStr
    # "local" (e-mail e senha), "google" ou "apple" — o front usa para saber se mostra "alterar senha".
    provider: str = Field(default="local", validation_alias="auth_provider")
    # caminho da foto na API (ex.: "/users/3/avatar?v=1729..."), ou null se não tiver foto
    avatar_url: Optional[str] = None

    @field_validator("provider", mode="before")
    @classmethod
    def _unwrap_provider(cls, value):
        return getattr(value, "value", value) or "local"

    @model_validator(mode="wrap")
    @classmethod
    def _avatar_url(cls, data, handler):
        out = handler(data)
        if out.avatar_url is None:
            out.avatar_url = avatar_url_for(data)
        return out

    class Config:
        from_attributes = True
        populate_by_name = True


class UserUpdate(BaseModel):
    """Campos editáveis do perfil (PATCH /auth/me). Mande só o que mudou."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    handle: Optional[str] = Field(default=None, pattern=r"^[a-z0-9._]{3,20}$")

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


class UserStats(BaseModel):
    translations: int  # traduções salvas no histórico
    lessons: int       # aulas concluídas (ainda não existe a função de aulas → sempre 0)
    badges: int        # selos conquistados (ainda não existe a função de selos → sempre 0)


class AvatarUpload(BaseModel):
    # data URL gerada pelo canvas do front: "data:image/jpeg;base64,...."
    image: str = Field(max_length=700_000)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


# ---------- Histórico ----------
class HistoryCreate(BaseModel):
    type: Literal["l", "t"]
    text: str = Field(min_length=1)


class HistoryOut(BaseModel):
    id: int
    type: Literal["l", "t"]
    text: str
    favorite: bool
    created_at: datetime

    # O SQLAlchemy retorna um membro de TranslationType (Enum), não a string crua;
    # normalizamos aqui para o Literal["l","t"] validar corretamente.
    @field_validator("type", mode="before")
    @classmethod
    def _unwrap_enum(cls, value):
        return getattr(value, "value", value)

    class Config:
        from_attributes = True


class HistoryFilter(BaseModel):
    type: Optional[Literal["l", "t"]] = None
    favorite: Optional[bool] = None
    search: Optional[str] = None


# ---------- Comunidades ----------
CommunityCategory = Literal["estudos", "saude", "trabalho", "cultura", "familia", "geral"]
CommunityIcon = Literal["cap", "building", "users", "heart", "book", "hand"]
CommunityColor = Literal["blue", "amber", "green", "pink", "purple"]


def _as_utc(value: datetime) -> datetime:
    """O SQLite devolve datas sem fuso (em UTC). Marcamos como UTC para o navegador
    converter certo para o horário local (senão "há 5 min" vira "há 3 h")."""
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class CommunityCreate(BaseModel):
    name: str = Field(min_length=3, max_length=60)
    description: str = Field(default="", max_length=280)
    category: CommunityCategory = "geral"
    icon: CommunityIcon = "users"
    color: CommunityColor = "blue"

    @field_validator("name", "description", mode="before")
    @classmethod
    def _strip(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


class CommunityOut(BaseModel):
    id: int
    name: str
    description: str
    category: str
    icon: str
    color: str
    member_count: int
    joined: bool
    is_owner: bool
    created_at: Optional[datetime] = None

    _utc = field_validator("created_at")(lambda cls, v: _as_utc(v))


class PostAuthor(BaseModel):
    id: int
    name: str
    handle: str
    avatar_url: Optional[str] = None


class PostCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)

    @field_validator("text", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class PostOut(BaseModel):
    id: int
    text: str
    created_at: datetime
    author: PostAuthor
    mine: bool
    can_delete: bool

    _utc = field_validator("created_at")(lambda cls, v: _as_utc(v))
