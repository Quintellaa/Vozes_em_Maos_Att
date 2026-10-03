"""Schemas Pydantic — contratos de entrada/saída da API (independentes dos modelos de DB)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Auth ----------
class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


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

    class Config:
        from_attributes = True


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
