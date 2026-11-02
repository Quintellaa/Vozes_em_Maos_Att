"""Rotas de comunidades: explorar, entrar/sair, criar e mural de posts."""
import unicodedata
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Community, CommunityMember, CommunityPost, User
from app.schemas import avatar_url_for, CommunityCategory, CommunityCreate, CommunityOut, PostCreate, PostOut

router = APIRouter(prefix="/communities", tags=["communities"])

# Comunidades iniciais, criadas uma única vez quando o banco ainda não tem nenhuma.
DEFAULT_COMMUNITIES = [
    ("Libras na Facu", "Estudantes trocando sinais de disciplinas, provas e vida acadêmica.", "estudos", "cap", "amber"),
    ("Saúde Inclusiva", "Profissionais e pacientes por um atendimento acessível em Libras.", "saude", "building", "blue"),
    ("Iniciantes em Libras", "Começando agora? Tire dúvidas e pratique o básico com a gente.", "estudos", "book", "green"),
    ("Libras no Trabalho", "Sinais do dia a dia profissional, entrevistas e inclusão nas empresas.", "trabalho", "users", "purple"),
    ("Cultura Surda", "Arte, história, poesia e eventos da comunidade surda.", "cultura", "hand", "pink"),
    ("Famílias de Surdos", "Pais, mães e parentes aprendendo juntos a se comunicar em Libras.", "familia", "heart", "pink"),
]


def seed_default_communities(db: Session) -> None:
    if db.query(Community).count() == 0:
        for name, description, category, icon, color in DEFAULT_COMMUNITIES:
            db.add(Community(name=name, description=description, category=category, icon=icon, color=color))
        db.commit()


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acento: "Saúde" e "saude" viram a mesma coisa na busca."""
    sem_acento = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def _member_counts(db: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    rows = (
        db.query(CommunityMember.community_id, func.count(CommunityMember.id))
        .filter(CommunityMember.community_id.in_(ids))
        .group_by(CommunityMember.community_id)
        .all()
    )
    return dict(rows)


def _joined_ids(db: Session, user: User, ids: list[int]) -> set[int]:
    if not ids:
        return set()
    rows = (
        db.query(CommunityMember.community_id)
        .filter(CommunityMember.user_id == user.id, CommunityMember.community_id.in_(ids))
        .all()
    )
    return {r[0] for r in rows}


def _to_out(communities: list[Community], user: User, db: Session) -> list[CommunityOut]:
    ids = [c.id for c in communities]
    counts = _member_counts(db, ids)
    joined = _joined_ids(db, user, ids)
    return [
        CommunityOut(
            id=c.id,
            name=c.name,
            description=c.description or "",
            category=c.category,
            icon=c.icon,
            color=c.color,
            member_count=counts.get(c.id, 0),
            joined=c.id in joined,
            is_owner=c.created_by == user.id,
            created_at=c.created_at,
        )
        for c in communities
    ]


def _get_community(community_id: int, db: Session) -> Community:
    community = db.get(Community, community_id)
    if not community:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comunidade não encontrada.")
    return community


def _is_member(db: Session, community_id: int, user: User) -> bool:
    return (
        db.query(CommunityMember)
        .filter(CommunityMember.community_id == community_id, CommunityMember.user_id == user.id)
        .first()
        is not None
    )


@router.get("", response_model=list[CommunityOut])
def list_communities(
    search: Optional[str] = None,
    category: Optional[CommunityCategory] = None,
    joined: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Community)
    if category:
        query = query.filter(Community.category == category)
    if joined is not None:
        mine = db.query(CommunityMember.community_id).filter(CommunityMember.user_id == current_user.id)
        query = query.filter(Community.id.in_(mine) if joined else ~Community.id.in_(mine))

    items = query.all()
    if search and search.strip():
        # Busca sem diferenciar acentos (o SQLite não faz isso sozinho). São poucas comunidades,
        # então filtrar aqui é simples; com milhares, mova para o banco (ex.: coluna normalizada).
        termo = _normalizar(search)
        items = [c for c in items if termo in _normalizar(c.name) or termo in _normalizar(c.description)]

    result = _to_out(items, current_user, db)
    # Mais populares primeiro; empate em ordem alfabética.
    result.sort(key=lambda c: (-c.member_count, c.name.lower()))
    return result


@router.post("", response_model=CommunityOut, status_code=status.HTTP_201_CREATED)
def create_community(
    payload: CommunityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exists = db.query(Community).filter(func.lower(Community.name) == payload.name.lower()).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma comunidade com esse nome.")

    community = Community(**payload.model_dump(), created_by=current_user.id)
    db.add(community)
    db.flush()
    db.add(CommunityMember(community_id=community.id, user_id=current_user.id))  # quem cria já entra
    db.commit()
    db.refresh(community)
    return _to_out([community], current_user, db)[0]


@router.get("/{community_id}", response_model=CommunityOut)
def get_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _to_out([_get_community(community_id, db)], current_user, db)[0]


@router.post("/{community_id}/join", response_model=CommunityOut)
def join_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = _get_community(community_id, db)
    if not _is_member(db, community_id, current_user):
        db.add(CommunityMember(community_id=community_id, user_id=current_user.id))
        db.commit()
    return _to_out([community], current_user, db)[0]


@router.delete("/{community_id}/join", response_model=CommunityOut)
def leave_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = _get_community(community_id, db)
    db.query(CommunityMember).filter(
        CommunityMember.community_id == community_id, CommunityMember.user_id == current_user.id
    ).delete()
    db.commit()
    return _to_out([community], current_user, db)[0]


def _post_out(post: CommunityPost, community: Community, user: User) -> PostOut:
    return PostOut(
        id=post.id,
        text=post.text,
        created_at=post.created_at,
        author={
            "id": post.author.id,
            "name": post.author.name,
            "handle": post.author.handle,
            "avatar_url": avatar_url_for(post.author),
        },
        mine=post.user_id == user.id,
        can_delete=post.user_id == user.id or community.created_by == user.id,
    )


@router.get("/{community_id}/posts", response_model=list[PostOut])
def list_posts(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = _get_community(community_id, db)
    posts = (
        db.query(CommunityPost)
        .filter(CommunityPost.community_id == community_id)
        .order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc())
        .limit(50)
        .all()
    )
    return [_post_out(p, community, current_user) for p in posts]


@router.post("/{community_id}/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    community_id: int,
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = _get_community(community_id, db)
    if not _is_member(db, community_id, current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Entre na comunidade para publicar.")
    if not payload.text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Escreva alguma coisa antes de publicar.")

    post = CommunityPost(community_id=community_id, user_id=current_user.id, text=payload.text)
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_out(post, community, current_user)


@router.delete("/{community_id}/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    community_id: int,
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    community = _get_community(community_id, db)
    post = db.get(CommunityPost, post_id)
    if not post or post.community_id != community_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publicação não encontrada.")
    if post.user_id != current_user.id and community.created_by != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você só pode apagar suas próprias publicações.")
    db.delete(post)
    db.commit()
