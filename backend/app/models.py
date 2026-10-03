"""Modelos de banco de dados (SQLAlchemy ORM)."""
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AuthProvider(str, enum.Enum):
    local = "local"
    google = "google"
    apple = "apple"


class TranslationType(str, enum.Enum):
    libras_to_text = "l"   # Libras → Texto (reconhecimento pela câmera)
    text_to_libras = "t"   # Texto → Libras (avatar)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    handle = Column(String(60), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # nulo para contas sociais (google/apple)
    auth_provider = Column(Enum(AuthProvider), nullable=False, default=AuthProvider.local)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    history = relationship("TranslationHistory", back_populates="user", cascade="all, delete-orphan")


class TranslationHistory(Base):
    __tablename__ = "translation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(TranslationType), nullable=False)
    text = Column(Text, nullable=False)
    favorite = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="history")
