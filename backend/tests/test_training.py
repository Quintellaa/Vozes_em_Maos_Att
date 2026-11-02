"""Teste do fluxo completo de treino: gravações (.json) → tools/train_and_export.py → API.

Usa gravações FALSAS, geradas aqui: cada "sinal" tem a mão num lugar diferente
do corpo e um movimento próprio; cada "pessoa" tem um jeito um pouco diferente
(posição na câmera, tamanho, tremida). Não diz nada sobre a acurácia real —
só garante que o encanamento todo funciona antes de o grupo gravar de verdade.
"""
import importlib.util
import json
import math
import random
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIGNS = {"OI": "oi", "AGUA": "água", "SIM": "sim"}
SIGNERS = ["ana", "bia", "caio"]


def _load_trainer():
    spec = importlib.util.spec_from_file_location("trainer", ROOT / "tools" / "train_and_export.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_clip(sign_index, rng, signer_shift):
    """Um clipe de ~25 frames no formato que o recognizer.js grava."""
    cx, cy, scale = 0.5 + signer_shift, 0.6, 0.25 + rng.uniform(-0.02, 0.02)
    frames = []
    for t in range(25):
        pose = [{"x": cx + rng.gauss(0, 0.01), "y": cy - 0.3 * scale, "z": 0} for _ in range(33)]
        pose[11] = {"x": cx + scale / 2, "y": cy, "z": 0}  # ombro esquerdo
        pose[12] = {"x": cx - scale / 2, "y": cy, "z": 0}  # ombro direito
        # cada sinal: mão numa altura diferente + um movimento circular próprio
        angle = t / 25 * 2 * math.pi * (sign_index + 1)
        wx = cx - 0.2 * scale + 0.05 * math.cos(angle) + rng.gauss(0, 0.01)
        wy = cy - (0.2 + 0.5 * sign_index) * scale + 0.05 * math.sin(angle) + rng.gauss(0, 0.01)
        hand = [{"x": wx + 0.01 * i * math.cos(sign_index + i), "y": wy - 0.01 * i, "z": 0} for i in range(21)]
        frames.append({"pose": pose, "hands": {"left": None, "right": hand}})
    return {"recorded_at": "2026-10-12T00:00:00Z", "frames": frames}


@pytest.fixture
def recordings(tmp_path):
    rng = random.Random(7)
    data_dir = tmp_path / "gravacoes"
    data_dir.mkdir()
    for s_idx, signer in enumerate(SIGNERS):
        for g_idx, (gloss, word) in enumerate(SIGNS.items()):
            payload = {
                "format": "sinaliza-recording-v1", "signer": signer, "gloss": gloss, "word": word,
                "coord_space": "aspect-v1",
                "detect_fps": 20, "created_at": "2026-10-12T00:00:00Z",
                "clips": [_fake_clip(g_idx, rng, signer_shift=0.05 * s_idx) for _ in range(8)],
            }
            (data_dir / f"sinal_{gloss}_{signer}.json").write_text(json.dumps(payload), encoding="utf-8")
    (data_dir / "lixo.json").write_text("isto não é json")  # deve ser ignorado sem quebrar
    return data_dir


def test_treino_avalia_e_exporta(recordings, tmp_path):
    out = tmp_path / "modelo.joblib"
    bundle = _load_trainer().main(
        ["--data", str(recordings), "--out", str(out), "--report", str(tmp_path / "relatorio.md")]
    )
    assert out.exists()
    assert sorted(bundle["classes"]) == sorted(SIGNS)
    assert bundle["words"]["AGUA"] == "água"
    assert bundle["signers"] == SIGNERS
    assert bundle["loso_accuracy"] > 0.8  # dados sintéticos bem separados

    report = (tmp_path / "relatorio.md").read_text(encoding="utf-8")
    assert "Por pessoa" in report and "Por sinal" in report


def test_api_usa_o_modelo_treinado(recordings, tmp_path, client, auth_headers, monkeypatch):
    from app.config import settings
    from app.routers import recognition

    out = tmp_path / "modelo.joblib"
    _load_trainer().main(["--data", str(recordings), "--out", str(out), "--report", str(tmp_path / "r.md")])

    monkeypatch.setattr(settings, "model_path", str(out))
    recognition.load_model_bundle.cache_clear()
    try:
        info = client.get("/recognition/info", headers=auth_headers).json()
        assert info["words"]["AGUA"] == "água"
        assert info["accuracy_new_person"] > 0.8

        clip = _fake_clip(1, random.Random(99), signer_shift=0.02)  # um "AGUA" novo
        body = client.post("/recognition/predict", json={"frames": clip["frames"]}, headers=auth_headers).json()
        assert body["gloss"] == "AGUA"
        assert body["word"] == "água"
    finally:
        recognition.load_model_bundle.cache_clear()  # volta pro modelo padrão nos outros testes


def test_aumento_de_dados_espelha_e_mantem_formato():
    import numpy as np
    trainer = _load_trainer()
    clip = _fake_clip(0, random.Random(1), signer_shift=0)["frames"]
    rng = np.random.default_rng(0)

    normal = trainer.augment_clip(clip, rng, mirror=False)
    assert all(set(f) == {"pose", "hands"} for f in normal)
    assert any(f["hands"]["right"] for f in normal)          # mão continua na direita

    espelhado = trainer.augment_clip(clip, rng, mirror=True)
    # virou mão esquerda (de propósito o aumento também simula rótulo piscando e mão
    # "fantasma" em alguns quadros, então a maioria — não todos — é esquerda)
    n_esq = sum(1 for f in espelhado if f["hands"]["left"])
    n_dir = sum(1 for f in espelhado if f["hands"]["right"])
    assert n_esq > 2 * n_dir
    # o extrator da API aceita o resultado
    from app.libras_features import clip_to_features
    assert clip_to_features(espelhado) is not None


def test_aumento_simula_rotulo_piscando_e_mao_fantasma():
    """O aumento reproduz os dois defeitos do MediaPipe vistos nas gravações reais."""
    import numpy as np
    trainer = _load_trainer()
    clip = _fake_clip(0, random.Random(1), signer_shift=0)["frames"] * 8  # clipe longo = mais chances
    rng = np.random.default_rng(3)
    vistos_os_dois_lados = vistos_fantasma = False
    for _ in range(10):
        for f in trainer.augment_clip(clip, rng, mirror=False):
            h = f["hands"]
            vistos_os_dois_lados |= bool(h["left"] and not h["right"])   # rótulo trocado
            vistos_fantasma |= bool(h["left"] and h["right"])            # as duas mãos num quadro
    assert vistos_os_dois_lados and vistos_fantasma
