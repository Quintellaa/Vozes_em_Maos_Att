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
TTA_TRIMS = ((0.12, 0.0), (0.0, 0.12), (0.1, 0.1))  # (fração cortada do começo, do fim)


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


class Alternative(BaseModel):
    gloss: str
    confidence: float
    word: str | None = None  # palavra em português ("água"), quando o modelo traz




class PredictResponse(BaseModel):
    gloss: str | None  # None quando a confiança fica abaixo do mínimo
    confidence: float
    word: str | None = None  # palavra pra exibir/falar; vem do modelo (ver tools/)
    # Os 3 sinais mais prováveis, do maior pro menor. Serve pra depurar ("ele
    # confundiu com quê?") e pra mostrar palpites quando a confiança é baixa.
    alternatives: list[Alternative] = []


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


def _trim(frames, start_share, end_share):
    """Tira uma fração do começo e do fim dos quadros COM mão (o recorte do sinal
    nunca é perfeito: pode sobrar um pedaço da mão subindo ou descendo)."""
    detected = [i for i, f in enumerate(frames) if f["hands"]["left"] or f["hands"]["right"]]
    if len(detected) < 3 * MIN_DETECTED_FRAMES:
        return None
    a = detected[0] + int(len(detected) * start_share)
    b = detected[-1] - int(len(detected) * end_share)
    return frames[a:b + 1]


def predict_probabilities(model, frames, feature_version, features):
    """Probabilidade de cada sinal.

    Pra modelos da v3 em diante, em vez de olhar o recorte uma vez só, olhamos
    também com um pouco do começo e/ou do fim cortado e fazemos a MÉDIA. Se o
    recorte pegou um pedaço a mais ou a menos, uma das visões costuma acertar,
    e a média não se deixa levar por uma visão ruim. Modelos antigos (MINDS)
    continuam com a previsão simples, igual ao que foram treinados.
    """
    probs = [model.predict_proba(features.reshape(1, -1))[0]]
    if feature_version == "pose-hands-v3":
        for start, end in TTA_TRIMS:
            trimmed = _trim(frames, start, end)
            extra = None if trimmed is None else clip_to_features(trimmed, feature_version)
            if extra is not None:
                probs.append(model.predict_proba(extra.reshape(1, -1))[0])
    return np.mean(probs, axis=0)


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
    words = bundle.get("words", {})  # modelos antigos (MINDS) não têm esse mapa
    probabilities = predict_probabilities(model, frames, bundle["feature_version"], features)
    ranking = np.argsort(probabilities)[::-1]  # índices do mais provável pro menos
    best = int(ranking[0])
    confidence = float(probabilities[best])
    gloss = str(model.classes_[best]) if confidence >= settings.min_confidence else None
    alternatives = [
        Alternative(
            gloss=str(model.classes_[i]),
            confidence=float(probabilities[i]),
            word=words.get(str(model.classes_[i])),
        )
        for i in ranking[:3]
    ]
    return PredictResponse(
        gloss=gloss,
        confidence=confidence,
        word=words.get(gloss) if gloss else None,
        alternatives=alternatives,
    )


@router.get("/info")
def info(current_user: User = Depends(get_current_user)):
    """Diz se o modelo está disponível e quais sinais ele conhece."""
    try:
        bundle = load_model_bundle()
    except Exception as err:
        return {"available": False, "detail": str(err)}
    return {
        "available": True,
        "classes": [str(c) for c in bundle["classes"]],
        "words": bundle.get("words", {}),
        "accuracy_new_person": bundle.get("loso_accuracy"),  # medida no treino (ver tools/)
        "feature_version": bundle["feature_version"],
        "current_feature_version": FEATURE_VERSION,
        "n_training_clips": bundle.get("n_training_clips"),
        "excluded_signers": bundle.get("excluded_signers", []),
    }
