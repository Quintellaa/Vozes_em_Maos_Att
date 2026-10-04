"""Rota de reconhecimento de Libras: landmarks -> sinal.

O navegador detecta a mão (MediaPipe) e manda só os 21 pontos por frame — o
vídeo não sai do dispositivo. Aqui aplicamos o modelo treinado em
tools/train_and_export.py.
"""
import functools
import pathlib

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import get_current_user
from app.libras_features import EXTRACTORS, FEATURE_VERSION, MIN_DETECTED_FRAMES, clip_to_features
from app.models import User

router = APIRouter(prefix="/recognition", tags=["recognition"])

MAX_FRAMES = 600  # ~20s a 30fps; evita payloads absurdos


class Landmark(BaseModel):
    x: float
    y: float
    z: float


class Hands(BaseModel):
    left: list[Landmark] | None = Field(default=None, min_length=21, max_length=21)
    right: list[Landmark] | None = Field(default=None, min_length=21, max_length=21)


class Frame(BaseModel):
    """Um frame de vídeo. Campos None = nada detectado naquele frame.

    `hand` é o formato antigo (uma mão só) e continua aceito pra não quebrar
    clientes antigos; o formato atual manda `hands` (as duas) e `pose`.
    """
    hands: Hands | None = None
    pose: list[Landmark] | None = Field(default=None, min_length=33, max_length=33)
    hand: list[Landmark] | None = Field(default=None, min_length=21, max_length=21)


class PredictRequest(BaseModel):
    frames: list[Frame] = Field(min_length=MIN_DETECTED_FRAMES, max_length=MAX_FRAMES)


class PredictResponse(BaseModel):
    gloss: str | None  # None quando a confiança fica abaixo do mínimo
    confidence: float


@functools.lru_cache(maxsize=1)
def load_model_bundle():
    """Carrega o modelo uma vez e mantém em memória (lru_cache = carrega no 1º uso)."""
    import joblib  # importado aqui pra API subir mesmo sem as libs de ML instaladas

    path = pathlib.Path(settings.model_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado em '{path}'. Gere-o com tools/train_and_export.py "
            f"e copie o .joblib pra essa pasta."
        )

    bundle = joblib.load(path)
    saved_version = bundle.get("feature_version")
    if saved_version not in EXTRACTORS:
        # Proteção contra o pior tipo de bug: características calculadas de um jeito
        # no treino e de outro aqui. Melhor recusar do que prever errado em silêncio.
        raise ValueError(
            f"Modelo incompatível: foi treinado com características '{saved_version}', "
            f"desconhecidas nesta versão da API (conhecidas: {', '.join(sorted(EXTRACTORS))}). "
            f"Treine de novo com o código atual."
        )
    return bundle


@router.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        bundle = load_model_bundle()
    except (FileNotFoundError, ValueError) as err:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(err))
    except Exception as err:  # versão de scikit-learn incompatível, arquivo corrompido etc.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Não foi possível carregar o modelo de reconhecimento: {err}",
        )

    def dump(points):
        return None if points is None else [p.model_dump() for p in points]

    frames = [{
        "pose": dump(f.pose),
        "hands": {"left": dump(f.hands.left), "right": dump(f.hands.right)} if f.hands
                 else {"left": None, "right": dump(f.hand)},
    } for f in payload.frames]

    # A versão das características vem do MODELO carregado, não do código: assim
    # um modelo antigo continua recebendo exatamente o que ele aprendeu.
    features = clip_to_features(frames, bundle["feature_version"])
    if features is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Mão detectada em poucos frames (mínimo {MIN_DETECTED_FRAMES}).",
        )

    model = bundle["model"]
    probabilities = model.predict_proba(features.reshape(1, -1))[0]
    best = int(np.argmax(probabilities))
    confidence = float(probabilities[best])
    gloss = str(model.classes_[best]) if confidence >= settings.min_confidence else None
    return PredictResponse(gloss=gloss, confidence=confidence)


@router.get("/info")
def info(current_user: User = Depends(get_current_user)):
    """Diz se o modelo está disponível e quais sinais ele conhece."""
    try:
        bundle = load_model_bundle()
    except Exception as err:
        return {"available": False, "detail": str(err)}
    return {
        "available": True,
        "classes": bundle["classes"],
        "feature_version": bundle["feature_version"],
        "current_feature_version": FEATURE_VERSION,
        "n_training_clips": bundle.get("n_training_clips"),
        "excluded_signers": bundle.get("excluded_signers", []),
    }
