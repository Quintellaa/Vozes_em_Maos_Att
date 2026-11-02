"""Testes do reconhecimento de Libras: extração de características + rota /recognition."""
import random

import numpy as np

from app.libras_features import FEATURES_V3_SIZE, FEATURE_VERSION, N_FRAMES, ROW_SIZE, clip_to_features


# ---------- geradores de frames falsos (mesmo formato que o recognizer.js envia) ----------
def _ponto(rng):
    return {"x": rng.uniform(0.3, 0.7), "y": rng.uniform(0.3, 0.7), "z": rng.uniform(-0.05, 0.05)}


def _clip(n_frames=20, seed=0, com_mao=True):
    rng = random.Random(seed)
    return [{
        "pose": [_ponto(rng) for _ in range(33)],
        "hands": {"right": [_ponto(rng) for _ in range(21)] if com_mao else None, "left": None},
    } for _ in range(n_frames)]


def _transformar(frames, dx=0.0, dy=0.0, escala=1.0):
    """Simula a pessoa mais longe/perto da câmera (escala) e mais pro lado (dx, dy)."""
    def t(p):
        return {"x": 0.5 + (p["x"] - 0.5) * escala + dx,
                "y": 0.5 + (p["y"] - 0.5) * escala + dy,
                "z": p["z"] * escala}
    out = []
    for f in frames:
        hands = {k: (None if v is None else [t(p) for p in v]) for k, v in f["hands"].items()}
        out.append({"pose": [t(p) for p in f["pose"]], "hands": hands})
    return out


# ---------- características ----------
def test_tamanho_do_vetor():
    # versão antiga (usada pelo modelo do MINDS)
    assert clip_to_features(_clip(), "pose-hands-v1").shape == (N_FRAMES * ROW_SIZE,)
    # versão atual
    assert FEATURE_VERSION == "pose-hands-v3"
    assert clip_to_features(_clip()).shape == (FEATURES_V3_SIZE,)


def test_poucos_frames_com_mao_retorna_none():
    assert clip_to_features(_clip(com_mao=False)) is None


def test_nao_muda_com_distancia_ou_posicao_na_camera():
    for version in ("pose-hands-v1", "pose-hands-v3"):
        _checa_distancia(version)


def _checa_distancia(version):
    """É o que o docstring de libras_features.py promete: tudo é relativo ao corpo."""
    original = clip_to_features(_clip(seed=1), version)
    movido = clip_to_features(_transformar(_clip(seed=1), dx=0.15, dy=-0.1, escala=0.6), version)
    # tolerância pequena: o "+ 1e-6" que evita divisão por zero gera diferenças
    # relativas da ordem de 1e-5 — irrelevantes pro modelo
    assert np.allclose(original, movido, rtol=1e-4, atol=1e-4)


# ---------- rota ----------
def test_info_lista_os_20_sinais(client, auth_headers):
    info = client.get("/recognition/info", headers=auth_headers).json()
    assert info["available"] is True
    assert len(info["classes"]) == 20
    assert "BANHEIRO" in info["classes"]


def test_predict_responde_com_confianca(client, auth_headers):
    r = client.post("/recognition/predict", json={"frames": _clip()}, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["confidence"] <= 1.0
    # ruído aleatório não deve virar um sinal com confiança alta
    assert body["gloss"] is None or body["confidence"] >= 0.25
    # 3 palpites, em ordem decrescente, e o primeiro é o próprio resultado
    confs = [a["confidence"] for a in body["alternatives"]]
    assert len(confs) == 3 and confs == sorted(confs, reverse=True)
    assert confs[0] == body["confidence"]


def test_predict_sem_mao_retorna_422(client, auth_headers):
    r = client.post("/recognition/predict", json={"frames": _clip(com_mao=False)}, headers=auth_headers)
    assert r.status_code == 422


def test_predict_exige_login(client):
    assert client.post("/recognition/predict", json={"frames": _clip()}).status_code == 401


def test_v2_nao_liga_pra_qual_mao_foi_usada():
    """Mesmo sinal feito com a mão direita ou espelhado (mão esquerda) = mesmos números."""
    from app.libras_features import _mirror_frame
    clip = _clip(seed=3)
    espelhado = [_mirror_frame(f) for f in clip]
    assert all(f["hands"]["left"] and not f["hands"]["right"] for f in espelhado)
    a = clip_to_features(clip, "pose-hands-v2")
    b = clip_to_features(espelhado, "pose-hands-v2")
    assert np.allclose(a, b, atol=1e-6)
    # a v1 (modelo antigo) continua igual a antes: lá a mão importa
    assert not np.allclose(clip_to_features(clip, "pose-hands-v1"), clip_to_features(espelhado, "pose-hands-v1"))


# ---------- v3: problemas que apareceram nas gravações reais de webcam ----------
def _clip_mao_real(n=24, seed=5):
    """Pose fixa e UMA mão que se mexe: o que a webcam vê num sinal de uma mão só."""
    rng = random.Random(seed)
    pose = [{"x": 0.5, "y": 0.4, "z": 0.0} for _ in range(33)]
    pose[11] = {"x": 0.65, "y": 0.75, "z": 0.0}
    pose[12] = {"x": 0.35, "y": 0.75, "z": 0.0}
    base = [{"x": rng.uniform(-0.04, 0.04), "y": rng.uniform(-0.09, 0.0), "z": rng.uniform(-0.02, 0.02)} for _ in range(21)]
    base[0] = {"x": 0.0, "y": 0.0, "z": 0.0}
    base[9] = {"x": 0.0, "y": -0.09, "z": 0.0}
    frames = []
    for t in range(n):
        cx, cy = 0.4 + 0.004 * t, 0.55 - 0.003 * t
        hand = [{"x": cx + p["x"], "y": cy + p["y"], "z": p["z"]} for p in base]
        frames.append({"pose": pose, "hands": {"left": None, "right": hand}})
    return frames


def _igual(a, b, tol=1e-6):
    return a is not None and b is not None and np.allclose(a, b, atol=tol)


def test_v3_mao_fantasma_nao_muda_o_resultado():
    """O MediaPipe às vezes detecta a MESMA mão duas vezes, com o outro rótulo."""
    limpo = _clip_mao_real()
    com_fantasma = [dict(f, hands={"right": f["hands"]["right"],
                                   "left": [dict(p, x=p["x"] + 0.004) for p in f["hands"]["right"]] if i % 4 == 1 else None})
                    for i, f in enumerate(limpo)]
    a, b = clip_to_features(limpo), clip_to_features(com_fantasma)
    assert np.abs(a - b).max() < 0.2   # perto (o deslocamento do fantasma pode escolher a cópia), não uma 2ª mão
    # a v2, de propósito, NÃO resolvia isso (documenta o motivo da v3)
    assert not np.allclose(clip_to_features(limpo, "pose-hands-v2"), clip_to_features(com_fantasma, "pose-hands-v2"), atol=0.05)


def test_v3_rotulo_piscando_nao_muda_o_resultado():
    limpo = _clip_mao_real()
    piscando = []
    for i, f in enumerate(limpo):
        h = f["hands"]
        piscando.append(dict(f, hands={"left": h["right"], "right": None}) if i in (0, 1, 7) else f)
    assert _igual(clip_to_features(limpo), clip_to_features(piscando))


def test_v3_buraco_curto_e_preenchido():
    limpo = _clip_mao_real()
    buraco = [dict(f, hands={"left": None, "right": None}) if i in (10, 11) else f for i, f in enumerate(limpo)]
    a, b = clip_to_features(limpo), clip_to_features(buraco)
    assert np.abs(a - b).max() < 1e-3  # o movimento é uma reta: a interpolação reconstrói quase igual


def test_v3_canhoto_e_destro_dao_o_mesmo():
    from app.libras_features import _mirror_frame
    clip = _clip_mao_real()
    assert _igual(clip_to_features(clip), clip_to_features([_mirror_frame(f) for f in clip]), tol=1e-5)


def test_v3_duas_maos_continuam_diferentes_de_uma():
    um = _clip_mao_real()
    dois = []
    for f in um:
        outra = [dict(p, x=p["x"] + 0.3) for p in f["hands"]["right"]]
        dois.append(dict(f, hands={"right": f["hands"]["right"], "left": outra}))
    assert not np.allclose(clip_to_features(um), clip_to_features(dois), atol=0.05)


def test_v3_aceita_formato_antigo_de_uma_mao():
    clip = [{"pose": f["pose"], "hand": f["hands"]["right"]} for f in _clip_mao_real()]
    assert clip_to_features(clip) is not None
