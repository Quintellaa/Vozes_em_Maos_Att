"""libras_features.py — converte frames de landmarks num vetor de características.

ESTE ARQUIVO EXISTE EM DOIS LUGARES E AS DUAS CÓPIAS PRECISAM SER IDÊNTICAS:
    tools/libras_features.py          (treino)
    backend/app/libras_features.py    (inferência na API)

Se mudar um, mude o outro. Qualquer diferença faz o modelo receber na previsão
números diferentes dos que viu no treino, e as previsões ficam erradas sem dar
erro nenhum. Por isso a versão usada é gravada junto com o modelo e conferida
na hora de carregar.

DUAS VERSÕES CONVIVEM AQUI:

  "hand-v1"        — só uma mão, sem referência ao corpo. É o que o primeiro
                     modelo usou. Fica aqui pra modelos antigos continuarem
                     funcionando.

  "pose-hands-v1"  — AS DUAS mãos + posição em relação ao CORPO (ombros).
                     Em Libras o mesmo formato de mão em lugares diferentes do
                     corpo é um sinal diferente, e "hand-v1" era cego pra isso.
                     Esta é a versão atual.

FORMATO DOS FRAMES (o mesmo pros dois extratores):
    {"pose":  [33 pontos {x,y,z}] ou None,
     "hands": {"left": [21 pontos] ou None, "right": [21 pontos] ou None}}
"""
import numpy as np

FEATURE_VERSION = "pose-hands-v1"

N_FRAMES = 32
MIN_DETECTED_FRAMES = 5
WRIST, MIDDLE_MCP = 0, 9                         # índices da mão (padrão MediaPipe)
NOSE, LEFT_SHOULDER, RIGHT_SHOULDER = 0, 11, 12  # índices da pose (padrão MediaPipe)
HAND_SLOTS = ("right", "left")
ROW_SIZE = 2 + 2 * (1 + 2 + 63)                  # nariz + (presença, posição, forma) por mão


def frame_hands(frame):
    """Lê as mãos de um frame, aceitando também o formato antigo {"hand": [...]}."""
    if "hands" in frame:
        hands = frame.get("hands") or {}
        return hands.get("left"), hands.get("right")
    single = frame.get("hand")  # formato antigo: uma mão só
    return None, single


def _resample(rows):
    """Reamostra uma matriz [n, d] pra [N_FRAMES, d], interpolando os NaN pelo caminho."""
    flat = np.asarray(rows, dtype=float)
    n = len(flat)
    t = np.arange(n)
    for col in range(flat.shape[1]):
        known = ~np.isnan(flat[:, col])
        if not known.any():
            flat[:, col] = 0.0
        else:
            flat[:, col] = np.interp(t, t[known], flat[known, col])
    t_new = np.linspace(0, n - 1, N_FRAMES)
    return np.stack([np.interp(t_new, t, flat[:, c]) for c in range(flat.shape[1])], axis=1)


def _hand_shape(points):
    """Forma da mão: 21 pontos relativos ao pulso, na escala do tamanho da mão."""
    pts = np.array([[p["x"], p["y"], p["z"]] for p in points])
    size = np.linalg.norm(pts[MIDDLE_MCP, :2] - pts[WRIST, :2]) + 1e-6
    return ((pts - pts[WRIST]) / size).ravel()


# ---------------------------------------------------------------- hand-v1
def clip_to_features_hand_v1(frames):
    """Versão antiga: uma mão, sem referência ao corpo. Mantida por compatibilidade."""
    def pick(frame):
        left, right = frame_hands(frame)
        return right or left

    detected = [i for i, f in enumerate(frames) if pick(f) is not None]
    if len(detected) < MIN_DETECTED_FRAMES:
        return None

    first, last = detected[0], detected[-1]
    rows = []
    for i in range(first, last + 1):
        hand = pick(frames[i])
        rows.append([np.nan] * 63 if hand is None
                    else [c for p in hand for c in (p["x"], p["y"], p["z"])])

    pts = _resample(rows).reshape(N_FRAMES, 21, 3)
    hand_size = np.median(np.linalg.norm(pts[:, MIDDLE_MCP, :2] - pts[:, WRIST, :2], axis=1)) + 1e-6
    shape = (pts - pts[:, WRIST:WRIST + 1, :]) / hand_size
    motion = (pts[:, WRIST, :2] - pts[0, WRIST, :2]) / hand_size
    return np.concatenate([shape.ravel(), motion.ravel()])


# -------------------------------------------------------- pose-hands-v1
def clip_to_features_pose_hands_v1(frames):
    """Versão atual: duas mãos + onde elas estão em relação ao corpo.

    Por frame guardamos, pra cada mão (direita e esquerda):
      - se ela aparece (1/0);
      - ONDE o pulso está em relação ao meio dos ombros, na escala da largura
        dos ombros — é isso que diz se o sinal acontece perto do rosto, do
        peito ou do ombro;
      - a FORMA da mão (21 pontos relativos ao próprio pulso).
    Mais a posição do nariz, como referência da cabeça.

    Como tudo é medido em relação ao corpo, não muda se a pessoa estiver mais
    perto ou mais longe da câmera, nem mais pra um lado do quadro.
    """
    def any_hand(frame):
        left, right = frame_hands(frame)
        return left is not None or right is not None

    detected = [i for i, f in enumerate(frames) if any_hand(f)]
    if len(detected) < MIN_DETECTED_FRAMES:
        return None

    first, last = detected[0], detected[-1]
    rows = []
    for i in range(first, last + 1):
        frame = frames[i]
        left, right = frame_hands(frame)
        pose = frame.get("pose")

        if pose is None:
            rows.append([np.nan] * ROW_SIZE)  # interpolado depois a partir dos vizinhos
            continue

        ls = np.array([pose[LEFT_SHOULDER]["x"], pose[LEFT_SHOULDER]["y"]])
        rs = np.array([pose[RIGHT_SHOULDER]["x"], pose[RIGHT_SHOULDER]["y"]])
        center = (ls + rs) / 2
        scale = np.linalg.norm(ls - rs) + 1e-6

        nose = np.array([pose[NOSE]["x"], pose[NOSE]["y"]])
        row = list((nose - center) / scale)

        for slot in HAND_SLOTS:
            hand = right if slot == "right" else left
            if hand is None:
                row += [0.0] * (1 + 2 + 63)
                continue
            wrist = np.array([hand[WRIST]["x"], hand[WRIST]["y"]])
            row += [1.0]
            row += list((wrist - center) / scale)  # ONDE no corpo
            row += list(_hand_shape(hand))         # FORMA da mão
        rows.append(row)

    return _resample(rows).ravel()


EXTRACTORS = {
    "hand-v1": clip_to_features_hand_v1,
    "pose-hands-v1": clip_to_features_pose_hands_v1,
}


def clip_to_features(frames, version=FEATURE_VERSION):
    """Extrai as características na versão pedida. Erra alto se a versão for desconhecida."""
    if version not in EXTRACTORS:
        raise ValueError(
            f"Versão de características desconhecida: '{version}'. "
            f"Conhecidas: {', '.join(sorted(EXTRACTORS))}."
        )
    return EXTRACTORS[version](frames)
