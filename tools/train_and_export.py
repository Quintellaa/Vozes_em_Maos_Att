"""train_and_export.py — treina o modelo de reconhecimento com as gravações do grupo.

USO (de dentro da pasta backend, com o .venv ativado):

    python ../tools/train_and_export.py

O que ele faz:
  1. Lê todos os arquivos .json de dados/gravacoes/ (gerados pela tela gravar.html).
  2. Transforma cada amostra em números com o MESMO código que a API usa
     (backend/app/libras_features.py) — importado daqui, não copiado, então
     treino e uso nunca ficam diferentes.
  3. AVALIA de um jeito honesto: treina com todas as pessoas MENOS UMA e testa
     na que ficou de fora; repete pra cada pessoa. Isso responde a pergunta que
     importa: "o app funciona com alguém que ele nunca viu?".
  4. AUMENTA OS DADOS: cada gravação de treino vira várias variações (mais
     rápida/lenta, câmera inclinada, tremida, frames perdidos, espelhada pra
     canhotos). Com poucas pessoas gravando, isso ajuda muito o modelo a
     funcionar com gente nova. As amostras de TESTE nunca são aumentadas.
  5. Compara 5 algoritmos (RF, Extra Trees, SVM, KNN, regressão logística) e fica com o melhor.
  6. Treina o modelo final com TODOS os dados e salva em backend/models/.
  7. Escreve um relatório (tools/relatorio_treino.md) com acurácia por pessoa,
     por sinal e quais sinais ele confunde — pronto pra virar slide.

Depois, aponte a API pro modelo novo no backend/.env:
    MODEL_PATH=models/libras_grupo.joblib
"""
import argparse
import datetime as dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))  # pra importar o extrator da API

from app.libras_features import FEATURE_VERSION, clip_to_features  # noqa: E402

RECORDING_FORMAT = "sinaliza-recording-v1"

# Pares esquerda/direita dos 33 pontos de pose do MediaPipe (pra espelhar).
POSE_MIRROR_PAIRS = [(1, 4), (2, 5), (3, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16),
                     (17, 18), (19, 20), (21, 22), (23, 24), (25, 26), (27, 28), (29, 30), (31, 32)]


# ----------------------------------------------------------------------------- aumento de dados
def _map_points(points, fn):
    return None if points is None else [fn(p) for p in points]


def augment_clip(frames, rng, mirror=False):
    """Gera UMA variação realista de um clipe (lista de frames no formato do recognizer.js).

    Tudo aqui imita coisas que mudam de verdade entre uma gravação e outra:
      - velocidade: a pessoa sinaliza mais rápido/devagar, ou acelera no meio;
      - inclinação: câmera ou corpo levemente tortos (±8°);
      - tremida: o MediaPipe não marca os pontos sempre no mesmo lugar;
      - frames perdidos: às vezes a mão não é detectada em alguns quadros;
      - espelho: um canhoto faz o sinal espelhado.
      - rótulo piscando e mão "fantasma": o MediaPipe às vezes troca esquerda/direita
        por 1–3 quadros e às vezes detecta a MESMA mão duas vezes (isso aparece nas
        gravações reais), então o treino também vê isso.
    (Distância e posição na câmera NÃO precisam de aumento: as características
    já são medidas em relação aos ombros, então não mudam com isso.)
    """
    n = len(frames)
    # velocidade: novo tamanho + "curva" do tempo (acelera/desacelera)
    new_len = max(5, int(round(n * rng.uniform(0.8, 1.25))))
    gamma = rng.uniform(0.8, 1.25)
    idx = np.clip(np.round((np.linspace(0, 1, new_len) ** gamma) * (n - 1)).astype(int), 0, n - 1)

    angle = np.deg2rad(rng.uniform(-8, 8))
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    noise = 0.004

    def center_of(frame):
        pose = frame.get("pose")
        if pose:
            return (pose[11]["x"] + pose[12]["x"]) / 2, (pose[11]["y"] + pose[12]["y"]) / 2
        return 0.5, 0.5

    out = []
    for i in idx:
        frame = frames[i]
        cx, cy = center_of(frame)

        def move(p):
            x, y = p["x"] - cx, p["y"] - cy
            x, y = x * cos_a - y * sin_a, x * sin_a + y * cos_a
            x, y = x + cx + rng.normal(0, noise), y + cy + rng.normal(0, noise)
            if mirror:
                x = 2 * cx - x
            return {"x": float(x), "y": float(y), "z": float(p["z"] + rng.normal(0, noise))}

        if "hands" in frame:
            left, right = (frame["hands"] or {}).get("left"), (frame["hands"] or {}).get("right")
        else:  # formato antigo, uma mão só
            left, right = None, frame.get("hand")
        pose = _map_points(frame.get("pose"), move)
        left, right = _map_points(left, move), _map_points(right, move)
        if mirror:
            left, right = right, left  # a mão esquerda vira a direita
            if pose:
                for a, b in POSE_MIRROR_PAIRS:
                    pose[a], pose[b] = pose[b], pose[a]
        # rótulo piscando: a mesma mão aparece como esquerda/direita trocada
        if (left is None) != (right is None) and rng.random() < 0.06:
            left, right = right, left
        # mão fantasma: a mesma mão detectada de novo com o outro rótulo, um pouco deslocada
        if (left is None) != (right is None) and rng.random() < 0.08:
            ghost = [{"x": q["x"] + rng.normal(0, 0.006), "y": q["y"] + rng.normal(0, 0.006), "z": q["z"]}
                     for q in (left or right)]
            if left is None:
                left = ghost
            else:
                right = ghost
        # frame perdido: o detector não achou as mãos nesse quadro
        if rng.random() < 0.10:
            left = right = None
        out.append({"pose": pose, "hands": {"left": left, "right": right}})
    return out


# ----------------------------------------------------------------------------- dados
def load_recordings(data_dir: Path, n_augment=0, mirror=True, seed=42):
    """Lê as gravações e devolve X (características), y (sinal), grupos (pessoa),
    palavras e, pra cada amostra, a lista das suas variações aumentadas."""
    X, y, groups, words, augmented = [], [], [], {}, []
    skipped = Counter()
    rng = np.random.default_rng(seed)

    files = sorted(data_dir.rglob("*.json"))
    if not files:
        sys.exit(f"Nenhum .json encontrado em {data_dir}. Grave sinais em gravar.html e coloque os arquivos lá.")

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"  [aviso] {path.name}: não é um JSON válido, ignorado")
            continue
        if data.get("format") != RECORDING_FORMAT:
            print(f"  [aviso] {path.name}: formato desconhecido, ignorado")
            continue

        if data.get("coord_space") != "aspect-v1":
            # Gravações feitas antes da correção de proporção (17/10) usam outra
            # escala de x. Misturar as duas confunde o modelo.
            print(f"  [aviso] {path.name}: gravação no formato antigo (antes da correção de "
                  f"proporção). Ignorada — regrave esse sinal.")
            continue
        gloss, signer = data["gloss"], data["signer"]
        words[gloss] = data.get("word", gloss.lower())
        for clip in data["clips"]:
            features = clip_to_features(clip["frames"], FEATURE_VERSION)
            if features is None:  # mão detectada em poucos frames
                skipped[gloss] += 1
                continue
            X.append(features)
            y.append(gloss)
            groups.append(signer)
            variations = []
            for k in range(n_augment):
                # ~1 em cada 3 variações é espelhada. Com as características
                # "pose-hands-v2" isso é neutralizado (ela põe a mão principal sempre
                # do mesmo lado), mas mantemos pra continuar valendo se a versão mudar.
                aug = clip_to_features(augment_clip(clip["frames"], rng, mirror=mirror and k % 3 == 2), FEATURE_VERSION)
                if aug is not None:
                    variations.append(aug)
            augmented.append(variations)

    if skipped:
        print(f"  [aviso] amostras descartadas por ter poucos frames com mão: {dict(skipped)}")
    return np.array(X), np.array(y), np.array(groups), words, augmented


def with_augmented(idx, X, y, augmented):
    """Junta as amostras originais `idx` com as variações aumentadas DELAS."""
    extra_X = [v for i in idx for v in augmented[i]]
    extra_y = [y[i] for i in idx for _ in augmented[i]]
    if not extra_X:
        return X[idx], y[idx]
    return np.vstack([X[idx], np.array(extra_X)]), np.concatenate([y[idx], np.array(extra_y)])


def print_counts(y, groups):
    signers = sorted(set(groups))
    glosses = sorted(set(y))
    width = max(len(g) for g in glosses) + 2
    print("\nAmostras por sinal e pessoa:")
    print(" " * width + "".join(f"{s[:10]:>12}" for s in signers) + f"{'TOTAL':>8}")
    for g in glosses:
        row = [int(np.sum((y == g) & (groups == s))) for s in signers]
        print(f"{g:<{width}}" + "".join(f"{n:>12}" for n in row) + f"{sum(row):>8}")
    return signers, glosses


# ----------------------------------------------------------------------------- modelos
def candidate_models():
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.decomposition import PCA
    from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC

    # Os 5 são testados com a mesma avaliação (pessoa de fora) e fica o melhor.
    # Com POUCAS gravações, KNN e regressão logística costumam ganhar; com muitas,
    # RF e SVM. Por isso testamos todos em vez de escolher no chute.
    return {
        # Random Forest: o que o projeto já usava. Robusto, não precisa normalizar.
        "rf": lambda: RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
        # SVM: costuma ir melhor com poucos dados. O SVM puro não dá "confiança" (%),
        # que a API precisa; o CalibratedClassifierCV acrescenta isso.
        "svm": lambda: make_pipeline(
            StandardScaler(),
            CalibratedClassifierCV(SVC(C=10, kernel="rbf"), cv=3, ensemble=False),
        ),
        # KNN ("vizinhos mais próximos"): compara o sinal com as gravações mais
        # parecidas. Simples de explicar e bom com poucos exemplos. O PCA resume
        # os ~4 mil números nas "direções" que explicam 90% da variação — sem isso, a distância
        # entre sinais fica dominada por ruído.
        "knn": lambda: make_pipeline(
            StandardScaler(), PCA(n_components=0.9, svd_solver="full"),
            KNeighborsClassifier(n_neighbors=5, weights="distance"),
        ),
        # Extra Trees: parecido com o RF, mas sorteia também os pontos de corte; costuma
        # ser mais estável quando há muitas características e poucas gravações.
        "et": lambda: ExtraTreesClassifier(n_estimators=400, random_state=42, n_jobs=-1),
        # Regressão logística: modelo linear, rápido e estável com poucos dados.
        "logreg": lambda: make_pipeline(
            StandardScaler(), LogisticRegression(C=0.1, max_iter=2000),
        ),
    }


def evaluate(make_model, X, y, groups, augmented):
    """Deixa uma pessoa de fora por vez. Se só houver 1 pessoa, cai pra validação cruzada comum."""
    from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold

    if len(set(groups)) >= 2:
        splits = list(LeaveOneGroupOut().split(X, y, groups))
        mode = "pessoa nova (treina sem a pessoa, testa nela)"
    else:
        n = min(5, min(Counter(y).values()))
        if n < 2:
            sys.exit("Poucas amostras: grave pelo menos 2 de cada sinal.")
        splits = list(StratifiedKFold(n_splits=n, shuffle=True, random_state=42).split(X, y))
        mode = f"validação cruzada {n}x (SÓ 1 PESSOA — acurácia vai parecer melhor do que é)"

    y_true, y_pred, per_group = [], [], {}
    for train_idx, test_idx in splits:
        model = make_model()
        model.fit(*with_augmented(train_idx, X, y, augmented))  # aumento SÓ no treino
        pred = model.predict(X[test_idx])                       # teste: só gravações reais
        y_true += list(y[test_idx])
        y_pred += list(pred)
        if len(set(groups)) >= 2:
            per_group[groups[test_idx][0]] = float(np.mean(pred == y[test_idx]))

    accuracy = float(np.mean(np.array(y_true) == np.array(y_pred)))
    return {"accuracy": accuracy, "per_group": per_group, "y_true": y_true, "y_pred": y_pred, "mode": mode}


# ----------------------------------------------------------------------------- relatório
def confusion(y_true, y_pred, labels):
    index = {g: i for i, g in enumerate(labels)}
    m = np.zeros((len(labels), len(labels)), dtype=int)
    for t, p in zip(y_true, y_pred):
        m[index[t], index[p]] += 1
    return m


def write_report(path, result, algo, all_results, labels, words, n_clips, signers):
    m = confusion(result["y_true"], result["y_pred"], labels)
    per_class = {g: (m[i, i] / m[i].sum() if m[i].sum() else 0.0) for i, g in enumerate(labels)}

    mixups = [(m[i, j], labels[i], labels[j]) for i in range(len(labels)) for j in range(len(labels))
              if i != j and m[i, j] > 0]
    mixups.sort(reverse=True)

    lines = [
        "# Relatório de treino — reconhecimento de Libras",
        "",
        f"- Data: {dt.datetime.now():%d/%m/%Y %H:%M}",
        f"- Amostras: {n_clips} · Sinais: {len(labels)} · Pessoas: {len(signers)} ({', '.join(signers)})",
        f"- Avaliação: {result['mode']}",
        f"- Algoritmo escolhido: **{algo.upper()}**",
        "",
        "## Acurácia",
        "",
        "| Algoritmo | Acurácia |",
        "|---|---|",
        *[f"| {a.upper()} | {r['accuracy']:.1%} |" for a, r in all_results.items()],
        "",
    ]
    if result["per_group"]:
        lines += ["## Por pessoa (testando em quem ficou fora do treino)", "", "| Pessoa | Acurácia |", "|---|---|",
                  *[f"| {g} | {a:.1%} |" for g, a in sorted(result["per_group"].items())], ""]
    lines += ["## Por sinal", "", "| Sinal | Acerto |", "|---|---|",
              *[f"| {words.get(g, g)} | {a:.1%} |" for g, a in sorted(per_class.items(), key=lambda kv: kv[1])], ""]
    if mixups:
        lines += ["## Confusões mais comuns", "", "| Era | Ele achou que era | Vezes |", "|---|---|---|",
                  *[f"| {words.get(t, t)} | {words.get(p, p)} | {n} |" for n, t, p in mixups[:10]], "",
                  "Se dois sinais se confundem muito, considere trocar um deles por um sinal mais diferente.", ""]
    lines += ["## Matriz de confusão (linha = sinal feito, coluna = sinal reconhecido)", "",
              "| | " + " | ".join(labels) + " |", "|---" * (len(labels) + 1) + "|",
              *[f"| **{labels[i]}** | " + " | ".join(str(v) for v in m[i]) + " |" for i in range(len(labels))], ""]
    path.write_text("\n".join(lines), encoding="utf-8")

    try:  # imagem da matriz pra slide (opcional: só se o matplotlib estiver instalado)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        names = [words.get(g, g) for g in labels]
        norm = m / np.maximum(m.sum(axis=1, keepdims=True), 1)
        fig, ax = plt.subplots(figsize=(1 + 0.6 * len(labels), 1 + 0.55 * len(labels)))
        ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(range(len(labels)), names, rotation=45, ha="right")
        ax.set_yticks(range(len(labels)), names)
        ax.set_xlabel("Reconhecido como")
        ax.set_ylabel("Sinal feito")
        for i in range(len(labels)):
            for j in range(len(labels)):
                if m[i, j]:
                    ax.text(j, i, m[i, j], ha="center", va="center", fontsize=8,
                            color="white" if norm[i, j] > 0.5 else "black")
        ax.set_title(f"Acurácia em pessoa nova: {result['accuracy']:.0%}")
        fig.tight_layout()
        fig.savefig(path.with_suffix(".png"), dpi=150)
        print(f"Imagem da matriz: {path.with_suffix('.png')}")
    except ImportError:
        print("(instale matplotlib se quiser a imagem da matriz de confusão: pip install matplotlib)")

    return per_class


# ----------------------------------------------------------------------------- main
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=ROOT / "dados" / "gravacoes")
    parser.add_argument("--out", type=Path, default=ROOT / "backend" / "models" / "libras_grupo.joblib")
    parser.add_argument("--report", type=Path, default=ROOT / "tools" / "relatorio_treino.md")
    parser.add_argument("--augment", type=int, default=8,
                        help="variações geradas por gravação de treino (0 desliga o aumento de dados)")
    parser.add_argument("--no-mirror", action="store_true",
                        help="não gerar variações espelhadas (use se todo mundo sinaliza com a mesma mão)")
    args = parser.parse_args(argv)

    import joblib
    import sklearn

    print(f"Lendo gravações de {args.data} ...")
    X, y, groups, words, augmented = load_recordings(args.data, args.augment, mirror=not args.no_mirror)
    n_aug = sum(len(a) for a in augmented)
    if n_aug:
        print(f"Aumento de dados: +{n_aug} variações geradas a partir de {len(y)} gravações (só pro treino).")
    signers, labels = print_counts(y, groups)
    if len(labels) < 2:
        sys.exit("Precisa de pelo menos 2 sinais diferentes pra treinar.")

    print("\nAvaliando (pode levar alguns minutos)...")
    all_results = {}
    for name, make_model in candidate_models().items():
        all_results[name] = evaluate(make_model, X, y, groups, augmented)
        r = all_results[name]
        print(f"  {name.upper():>4}: {r['accuracy']:.1%}"
              + (f"  (por pessoa: {', '.join(f'{g} {a:.0%}' for g, a in r['per_group'].items())})" if r["per_group"] else ""))

    # Em caso de empate, fica o primeiro da lista (RF, o mais simples de explicar).
    best = max(all_results, key=lambda k: all_results[k]["accuracy"])
    result = all_results[best]
    print(f"\nMelhor: {best.upper()} com {result['accuracy']:.1%} — {result['mode']}")

    per_class = write_report(args.report, result, best, all_results, labels, words, len(y), signers)
    worst = sorted(per_class.items(), key=lambda kv: kv[1])[:3]
    print("Sinais mais difíceis: " + ", ".join(f"{words.get(g, g)} {a:.0%}" for g, a in worst))
    print(f"Relatório: {args.report}")

    # Modelo final: treina com TODO mundo (a avaliação acima já mediu o que esperar).
    final = candidate_models()[best]()
    final.fit(*with_augmented(np.arange(len(y)), X, y, augmented))
    bundle = {
        "model": final,
        "classes": list(final.classes_),
        "words": words,
        "feature_version": FEATURE_VERSION,
        "sklearn_version": sklearn.__version__,
        "algorithm": best,
        "n_training_clips": int(len(y)),
        "n_augmented": int(n_aug),
        "signers": signers,
        "loso_accuracy": round(result["accuracy"], 4),
        "excluded_signers": [],
        "trained_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, args.out)
    print(f"\nModelo salvo em {args.out}")
    print("Pra usar: no backend/.env coloque MODEL_PATH=models/" + args.out.name + " e reinicie a API.")
    return bundle


if __name__ == "__main__":
    main()
