"""Rotas públicas de usuários (por enquanto só a foto de perfil)."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/avatar")
def get_avatar(user_id: int, db: Session = Depends(get_db)):
    """Devolve a foto como imagem. É pública (como em qualquer rede social) porque a tag
    <img> do navegador não manda o token. A URL muda quando a foto muda (?v=...),
    então dá para guardar em cache por bastante tempo."""
    user = db.get(User, user_id)
    if not user or not user.avatar:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto não encontrada.")
    return Response(
        content=user.avatar,
        media_type=user.avatar_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
