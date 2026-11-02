"""Modelos de banco de dados (SQLAlchemy ORM)."""
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
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
    # Foto de perfil (JPEG/PNG/WebP pequeno, já recortado pelo front) e quando mudou —
    # a data entra na URL da imagem para o navegador não mostrar a foto antiga do cache.
    avatar = Column(LargeBinary, nullable=True)
    avatar_type = Column(String(20), nullable=True)
    avatar_updated_at = Column(Integer, nullable=True)
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


# ---------- Comunidades ----------
class Community(Base):
    __tablename__ = "communities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(60), nullable=False)
    description = Column(String(280), nullable=False, default="")
    category = Column(String(20), nullable=False, default="geral")
    icon = Column(String(20), nullable=False, default="users")
    color = Column(String(20), nullable=False, default="blue")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("CommunityMember", back_populates="community", cascade="all, delete-orphan")
    posts = relationship("CommunityPost", back_populates="community", cascade="all, delete-orphan")


class CommunityMember(Base):
    __tablename__ = "community_members"
    __table_args__ = (UniqueConstraint("community_id", "user_id", name="uq_community_member"),)

    id = Column(Integer, primary_key=True)
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    community = relationship("Community", back_populates="members")


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    community_id = Column(Integer, ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    community = relationship("Community", back_populates="posts")
    author = relationship("User")
