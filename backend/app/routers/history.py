"""Rotas de histórico de traduções."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import TranslationHistory, User
from app.schemas import HistoryCreate, HistoryOut

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryOut])
def list_history(
    type: Optional[Literal["l", "t"]] = None,
    favorite: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(TranslationHistory).filter(TranslationHistory.user_id == current_user.id)
    if type is not None:
        query = query.filter(TranslationHistory.type == type)
    if favorite is not None:
        query = query.filter(TranslationHistory.favorite == favorite)
    if search:
        query = query.filter(TranslationHistory.text.ilike(f"%{search}%"))
    return query.order_by(TranslationHistory.created_at.desc()).limit(100).all()


@router.post("", response_model=HistoryOut, status_code=status.HTTP_201_CREATED)
def create_history_entry(
    payload: HistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = TranslationHistory(user_id=current_user.id, type=payload.type, text=payload.text)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _get_owned_entry(entry_id: int, current_user: User, db: Session) -> TranslationHistory:
    entry = db.get(TranslationHistory, entry_id)
    if not entry or entry.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro de histórico não encontrado.")
    return entry


@router.patch("/{entry_id}/favorite", response_model=HistoryOut)
def toggle_favorite(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _get_owned_entry(entry_id, current_user, db)
    entry.favorite = not entry.favorite
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _get_owned_entry(entry_id, current_user, db)
    db.delete(entry)
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(TranslationHistory).filter(TranslationHistory.user_id == current_user.id).delete()
    db.commit()
