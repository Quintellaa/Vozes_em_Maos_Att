"""libras_features.py — converte frames de landmarks num vetor de características.

ESTE É O ÚNICO LUGAR onde as características são calculadas. A API usa este
arquivo pra reconhecer, e tools/train_and_export.py IMPORTA este mesmo arquivo
pra treinar. Assim treino e uso nunca ficam diferentes (se ficassem, o modelo
receberia na previsão números diferentes dos que viu no treino, e erraria sem
dar erro nenhum). A versão usada é gravada junto com o modelo e conferida na
hora de carregar.

Se mudar o cálculo, crie uma VERSÃO NOVA em EXTRACTORS (não altere uma que já
existe) e treine de novo.

QUATRO VERSÕES CONVIVEM AQUI:

  "hand-v1"        — só uma mão, sem referência ao corpo. É o que o primeiro
                     modelo usou. Fica aqui pra modelos antigos continuarem
                     funcionando.

  "pose-hands-v1"  — AS DUAS mãos + posição em relação ao CORPO (ombros).
                     Em Libras o mesmo formato de mão em lugares diferentes do
                     corpo é um sinal diferente, e "hand-v1" era cego pra isso.
                     Usada pelo modelo provisório do MINDS-Libras.

  "pose-hands-v2"  — igual à v1, mas antes ESPELHA o sinal se a mão que mais
                     aparece é a esquerda. Assim o modelo não liga pra qual mão
                     foi usada: canhotos, destros e vídeos de celular salvos
                     espelhados (câmera frontal) viram a mesma coisa. Em Libras,
                     fazer o sinal com a outra mão é o mesmo sinal.
                     Usada pelos modelos treinados até 17/10.

  "pose-hands-v3"  — Esta é a versão atual. Resolve o que mais derrubava o
                     reconhecimento com gravações REAIS de webcam:
                       • o MediaPipe às vezes detecta a MESMA mão duas vezes
                         (uma como "esquerda", outra como "direita"): isso
                         aparecia como uma segunda mão fantasma. Agora as
                         detecções duplicadas são fundidas;
                       • o rótulo esquerda/direita "pisca" entre quadros. Agora
                         as mãos são seguidas pela posição (continuidade), e o
                         rótulo só decide o espelhamento do clipe todo;
                       • quadros perdidos no meio do sinal (1 a 4 seguidos) são
                         preenchidos por interpolação em vez de virarem "mão
                         sumiu";
                       • além das coordenadas, usa medidas que descrevem o
                         formato da mão sem depender do tamanho/ângulo (dedos
                         dobrados, distância entre pontas, orientação da palma,
                         ponta dos dedos e dedo indicador em relação ao rosto,
                         distância entre as duas mãos) e um resumo do clipe
                         inteiro (média, variação, caminho percorrido), que
                         não muda se a pessoa sinaliza um pouco mais rápido ou
                         mais devagar.

FORMATO DOS FRAMES (o mesmo pra todos os extratores):
    {"pose":  [33 pontos {x,y,z}] ou None,
     "hands": {"left": [21 pontos] ou None, "right": [21 pontos] ou None}}
"""
import numpy as np

FEATURE_VERSION = "pose-hands-v3"

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


# -------------------------------------------------------- pose-hands-v2
# Pares esquerda/direita dos 33 pontos de pose do MediaPipe (pra espelhar).
POSE_MIRROR_PAIRS = [(1, 4), (2, 5), (3, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16),
                     (17, 18), (19, 20), (21, 22), (23, 24), (25, 26), (27, 28), (29, 30), (31, 32)]


def _mirror_frame(frame):
    """Espelha um frame: inverte x e troca o que é esquerdo pelo que é direito.

    (Inverter o sinal de x basta: as características são medidas RELATIVAS ao
    corpo e ao pulso, então não importa onde o "espelho" fica.)"""
    flip = lambda pts: None if pts is None else [{"x": -p["x"], "y": p["y"], "z": p["z"]} for p in pts]
    left, right = frame_hands(frame)
    pose = flip(frame.get("pose"))
    if pose:
        for a, b in POSE_MIRROR_PAIRS:
            pose[a], pose[b] = pose[b], pose[a]
    return {"pose": pose, "hands": {"left": flip(right), "right": flip(left)}}


def clip_to_features_pose_hands_v2(frames):
    """v1 com a mão principal sempre no mesmo lado (ver docstring do arquivo)."""
    n_left = sum(1 for f in frames if frame_hands(f)[0] is not None)
    n_right = sum(1 for f in frames if frame_hands(f)[1] is not None)
    if n_left > n_right:
        frames = [_mirror_frame(f) for f in frames]
    return clip_to_features_pose_hands_v1(frames)


# -------------------------------------------------------- pose-hands-v3
# Constantes da v3 (as das versões antigas acima não mudam).
V3_FRAMES = 16               # quadros da sequência (mais que isso só repete informação)
DUPLICATE_HAND_DIST = 1.0    # mãos com pontos a menos de 1 "palma" de distância = a mesma mão detectada 2x
MAX_GAP_FILL = 4             # quadros seguidos sem mão que ainda preenchemos por interpolação
MIN_TWO_HAND_SHARE = 0.15    # menos que isso de quadros com as duas mãos = sinal de uma mão só
SAME_HAND_JUMP = 1.2         # em larguras de ombro: acima disso, a mão que apareceu é "outra"
TIP_IDS = (4, 8, 12, 16, 20)
INDEX_MCP, PINKY_MCP, INDEX_TIP = 5, 17, 8
HAND_FEATS = 1 + 2 + 10 + 2 + 2 + 60 + 5 + 5 + 3 + 3   # presença, pulso, pontas, rosto, forma, dobra, pontas-entre-si, palma, direção
ROW_SIZE_V3 = 2 + 2 * HAND_FEATS + 3                    # nariz + 2 mãos + relação entre as mãos
# colunas (dentro de cada mão) resumidas no clipe inteiro: pulso, dobra dos dedos, pontas entre si, palma, direção
_SUMMARY_COLS = list(range(1, 3)) + list(range(77, 93))
FEATURES_V3_SIZE = V3_FRAMES * ROW_SIZE_V3 + 2 * (1 + 2 * len(_SUMMARY_COLS)) + 6


def _pts_array(points):
    return np.array([[p["x"], p["y"], p["z"]] for p in points], dtype=float)


def _palm_scale(pts):
    """Tamanho da palma: média de 4 distâncias em 3D. Mais estável que só pulso→dedo médio,
    que vira ~0 quando a mão aponta pra câmera."""
    d = [np.linalg.norm(pts[a] - pts[b]) for a, b in ((WRIST, MIDDLE_MCP), (WRIST, INDEX_MCP),
                                                       (WRIST, PINKY_MCP), (INDEX_MCP, PINKY_MCP))]
    return float(np.mean(d)) + 1e-9


def _is_duplicate(a, b):
    """True se `a` e `b` são a mesma mão detectada duas vezes (rótulos diferentes, pontos quase iguais)."""
    pa, pb = _pts_array(a)[:, :2], _pts_array(b)[:, :2]
    return float(np.linalg.norm(pa - pb, axis=1).mean()) / _palm_scale(_pts_array(a)) < DUPLICATE_HAND_DIST


def _body_per_frame(frames):
    """Centro dos ombros, largura dos ombros e nariz por quadro, suavizados (mediana de 5 quadros)
    e com os quadros sem pose preenchidos pelo vizinho mais próximo."""
    n = len(frames)
    raw = np.full((n, 5), np.nan)
    for i, f in enumerate(frames):
        pose = f.get("pose")
        if pose:
            ls = np.array([pose[LEFT_SHOULDER]["x"], pose[LEFT_SHOULDER]["y"]])
            rs = np.array([pose[RIGHT_SHOULDER]["x"], pose[RIGHT_SHOULDER]["y"]])
            raw[i] = [*((ls + rs) / 2), np.linalg.norm(ls - rs), pose[NOSE]["x"], pose[NOSE]["y"]]
    known = np.where(~np.isnan(raw[:, 0]))[0]
    if len(known) == 0:  # sem pose nenhuma: valores neutros (o reconhecimento fica pior, mas não quebra)
        return np.tile([0.65, 0.7, 0.5, 0.65, 0.4], (n, 1))
    for c in range(5):
        raw[:, c] = np.interp(np.arange(n), known, raw[known, c])
    out = raw.copy()
    for i in range(n):
        out[i] = np.median(raw[max(0, i - 2):i + 3], axis=0)
    out[:, 2] = np.maximum(out[:, 2], 1e-3)
    return out


def _track_hands(frames, body):
    """Segue até 2 mãos pela POSIÇÃO, sem confiar no rótulo esquerda/direita do MediaPipe.

    Devolve (tracks, labels): tracks[k][i] = pontos da mão k no quadro i (ou None);
    labels[k][i] = rótulo que o MediaPipe deu (só usado pra decidir o espelhamento).
    """
    n = len(frames)
    tracks = [[None] * n, [None] * n]
    labels = [[None] * n, [None] * n]
    last = [None, None]                       # último pulso conhecido de cada mão (em larguras de ombro)
    norm = lambda pts, i: (pts[WRIST][:2] - body[i, :2]) / body[i, 2]

    for i, frame in enumerate(frames):
        left, right = frame_hands(frame)
        cands = [(lab, pts) for lab, pts in (("right", right), ("left", left)) if pts is not None]
        if not cands:
            continue
        if len(cands) == 2 and _is_duplicate(cands[0][1], cands[1][1]):
            # a mesma mão detectada duas vezes: fica a mais próxima de onde a mão estava
            ref = next((p for p in last if p is not None), None)
            pos = [norm(_pts_array(c[1]), i) for c in cands]
            pick = 0 if ref is None else int(np.argmin([np.linalg.norm(p - ref) for p in pos]))
            cands = [cands[pick]]

        wrists = [norm(_pts_array(pts), i) for _, pts in cands]
        if len(cands) == 1:
            dists = [np.inf if last[k] is None else np.linalg.norm(wrists[0] - last[k]) for k in (0, 1)]
            k = int(np.argmin(dists))
            if last[k] is None or (dists[k] > SAME_HAND_JUMP and last[1 - k] is None):
                k = 0 if last[0] is None else 1 if dists[0] > SAME_HAND_JUMP else 0
            assign = [(k, 0)]
        else:
            if last[0] is not None and last[1] is not None:
                same = sum(np.linalg.norm(wrists[c] - last[c]) for c in (0, 1))
                swap = sum(np.linalg.norm(wrists[c] - last[1 - c]) for c in (0, 1))
                order = (0, 1) if same <= swap else (1, 0)
            elif last[0] is not None or last[1] is not None:
                known = 0 if last[0] is not None else 1
                nearest = int(np.argmin([np.linalg.norm(w - last[known]) for w in wrists]))
                order = [None, None]
                order[nearest], order[1 - nearest] = known, 1 - known
            else:
                order = (0, 1) if wrists[0][0] <= wrists[1][0] else (1, 0)
            assign = [(order[c], c) for c in (0, 1)]
        for k, c in assign:
            tracks[k][i] = cands[c][1]
            labels[k][i] = cands[c][0]
            last[k] = wrists[c]
    return tracks, labels


def _fill_gaps(track, max_gap=MAX_GAP_FILL):
    """Preenche buracos curtos (1–4 quadros) de uma mão interpolando os 21 pontos."""
    present = [i for i, p in enumerate(track) if p is not None]
    out = list(track)
    for a, b in zip(present, present[1:]):
        if 1 < b - a <= max_gap + 1:
            pa, pb = _pts_array(track[a]), _pts_array(track[b])
            for i in range(a + 1, b):
                t = (i - a) / (b - a)
                pts = pa * (1 - t) + pb * t
                out[i] = [{"x": float(x), "y": float(y), "z": float(z)} for x, y, z in pts]
    return out


def _hand_row(points, body_i):
    """As HAND_FEATS características de uma mão num quadro."""
    center, scale, nose = body_i[:2], body_i[2], body_i[3:5]
    pts = _pts_array(points)
    ps = _palm_scale(pts)
    rel = (pts - pts[WRIST]) / ps                                   # forma, relativa ao pulso
    wrist = (pts[WRIST, :2] - center) / scale                       # ONDE no corpo
    tips = ((pts[list(TIP_IDS), :2] - center) / scale).ravel()      # pontas dos dedos no corpo
    palm_c = pts[[WRIST, INDEX_MCP, MIDDLE_MCP, 13, PINKY_MCP], :2].mean(axis=0)
    face = np.concatenate([(palm_c - nose) / scale, (pts[INDEX_TIP, :2] - nose) / scale])
    d = lambda a, b: np.linalg.norm(pts[a] - pts[b])
    curls = [d(8, WRIST) / (d(INDEX_MCP, WRIST) + 1e-9), d(12, WRIST) / (d(MIDDLE_MCP, WRIST) + 1e-9),
             d(16, WRIST) / (d(13, WRIST) + 1e-9), d(20, WRIST) / (d(PINKY_MCP, WRIST) + 1e-9),
             d(4, PINKY_MCP) / ps]
    tip_gaps = [d(4, 8) / ps, d(4, 12) / ps, d(8, 12) / ps, d(12, 16) / ps, d(16, 20) / ps]
    # (vetores unitários: só importa pra onde a palma/os dedos apontam, não o tamanho)
    unit = lambda v: v / (np.linalg.norm(v) + 1e-12)
    normal = unit(np.cross(unit(pts[INDEX_MCP] - pts[WRIST]), unit(pts[PINKY_MCP] - pts[WRIST])))
    direction = unit(pts[MIDDLE_MCP] - pts[WRIST])
    return np.concatenate([[1.0], wrist, tips, face, rel[1:].ravel(), curls, tip_gaps, normal, direction])


def _resample_rows(rows, n_out):
    t = np.linspace(0, len(rows) - 1, n_out)
    return np.stack([np.interp(t, np.arange(len(rows)), rows[:, c]) for c in range(rows.shape[1])], axis=1)


def clip_to_features_pose_hands_v3(frames):
    """Versão atual. Ver o docstring do arquivo (seção "pose-hands-v3")."""
    n_all = len(frames)
    body = _body_per_frame(frames)
    tracks, labels = _track_hands(frames, body)
    counts = [sum(p is not None for p in t) for t in tracks]
    both = sum(1 for i in range(n_all) if tracks[0][i] is not None and tracks[1][i] is not None)
    detected = sum(1 for i in range(n_all) if tracks[0][i] is not None or tracks[1][i] is not None)
    if detected < MIN_DETECTED_FRAMES:
        return None

    # mão principal = a que mais aparece (empate: a que o MediaPipe chama de "direita")
    rights = [sum(l == "right" for l in lab) for lab in labels]
    main = 0 if (counts[0], rights[0]) >= (counts[1], rights[1]) else 1
    second = 1 - main
    main_t, second_t = tracks[main], tracks[second]
    main_l, second_l = labels[main], labels[second]

    # sinal de UMA mão: o que sobrou na outra mão é ruído ou troca de mão — junta tudo na principal
    if both / detected < MIN_TWO_HAND_SHARE:
        main_t = [m if m is not None else s for m, s in zip(main_t, second_t)]
        main_l = [m if m is not None else s for m, s in zip(main_l, second_l)]
        second_t = [None] * n_all

    # espelha o clipe todo se a mão principal é a "esquerda" (canhotos = destros)
    mirror = sum(l == "left" for l in main_l if l) > sum(l == "right" for l in main_l if l)
    first = min(i for i in range(n_all) if main_t[i] is not None or second_t[i] is not None)
    last = max(i for i in range(n_all) if main_t[i] is not None or second_t[i] is not None)
    main_t, second_t = _fill_gaps(main_t), _fill_gaps(second_t)

    flip = lambda pts: [{"x": -p["x"], "y": p["y"], "z": p["z"]} for p in pts]
    body = body.copy()
    if mirror:
        body[:, 0] *= -1
        body[:, 3] *= -1
        main_t = [None if p is None else flip(p) for p in main_t]
        second_t = [None if p is None else flip(p) for p in second_t]

    rows = []
    zero_hand = np.zeros(HAND_FEATS)
    for i in range(first, last + 1):
        b = body[i]
        nose = (b[3:5] - b[:2]) / b[2]
        hands = [zero_hand if t[i] is None else _hand_row(t[i], b) for t in (main_t, second_t)]
        if main_t[i] is not None and second_t[i] is not None:
            w0 = (_pts_array(main_t[i])[WRIST, :2] - _pts_array(second_t[i])[WRIST, :2]) / b[2]
            between = [*w0, np.linalg.norm(w0)]
        else:
            between = [0.0, 0.0, 0.0]
        rows.append(np.concatenate([nose, hands[0], hands[1], between]))
    rows = np.array(rows)
    if len(rows) < 2:
        rows = np.vstack([rows, rows])

    sequence = _resample_rows(rows, V3_FRAMES)

    # ---- resumo do clipe inteiro (não muda se o sinal for um pouco mais rápido/lento) ----
    def summary(block):
        pres = rows[:, block] > 0.5
        out = [pres.mean()]
        cols = [block + c for c in _SUMMARY_COLS]
        vals = rows[pres][:, cols] if pres.any() else np.zeros((1, len(cols)))
        return out + list(vals.mean(axis=0)) + list(vals.std(axis=0))

    main_block, second_block = 2, 2 + HAND_FEATS
    wrist_path = rows[rows[:, main_block] > 0.5][:, main_block + 1:main_block + 3]
    path = float(np.linalg.norm(np.diff(wrist_path, axis=0), axis=1).sum()) if len(wrist_path) > 1 else 0.0
    net = (wrist_path[-1] - wrist_path[0]) if len(wrist_path) > 1 else np.zeros(2)
    both_rows = rows[:, -1] > 0
    stats = [
        *summary(main_block), *summary(second_block),
        float(rows[both_rows][:, -1].mean()) if both_rows.any() else 0.0,
        float(rows[both_rows][:, -1].min()) if both_rows.any() else 0.0,
        path, *net, len(rows) / 20.0,
    ]
    # (a 1ª posição é a presença; o resto são as colunas resumidas)
    return np.concatenate([sequence.ravel(), np.array(stats, dtype=float)])


EXTRACTORS = {
    "hand-v1": clip_to_features_hand_v1,
    "pose-hands-v1": clip_to_features_pose_hands_v1,
    "pose-hands-v2": clip_to_features_pose_hands_v2,
    "pose-hands-v3": clip_to_features_pose_hands_v3,
}


def clip_to_features(frames, version=FEATURE_VERSION):
    """Extrai as características na versão pedida. Erra alto se a versão for desconhecida."""
    if version not in EXTRACTORS:
        raise ValueError(
            f"Versão de características desconhecida: '{version}'. "
            f"Conhecidas: {', '.join(sorted(EXTRACTORS))}."
        )
    return EXTRACTORS[version](frames)
