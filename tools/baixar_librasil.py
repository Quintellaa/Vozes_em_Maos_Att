"""baixar_librasil.py — baixa da base V-LIBRASIL (UFPE) só os sinais da nossa lista.

A V-LIBRASIL tem 1.364 sinais, cada um feito por 3 intérpretes ("articuladores"),
1 vídeo por pessoa. O script baixa os vídeos dos sinais que batem com
frontend/js/recording-config.js e salva com o nome que a tela gravar.html entende:

    dados/librasil_videos/<GLOSA>__librasil_a<N>.mp4

Depois, em gravar.html → "Importar vídeo", selecione TODOS esses arquivos de uma
vez: o sinal e a pessoa saem do nome do arquivo, e sai um .json por vídeo.
Mova os .json de Downloads pra dados/gravacoes e treine normalmente.

Uso (na raiz do projeto):
    py -3.14 tools/baixar_librasil.py

Licença da V-LIBRASIL: uso para pesquisa e educação, citando a fonte
(RODRIGUES, A. J. "V-LIBRASIL: uma base de dados com sinais na Língua Brasileira
de Sinais (Libras)". Dissertação de Mestrado, UFPE, 2021). NÃO pode redistribuir
os vídeos sem permissão: não suba dados/librasil_videos pro GitHub nem no zip.
"""
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "dados" / "librasil_videos"

# O site da UFPE (libras.cin.ufpe.br) vive fora do ar. Esta cópia no Hugging Face
# tem os mesmos vídeos, com nome "<Sinal>_Articulador<N>.mp4".
HF_VIDEOS = "https://huggingface.co/datasets/SchberGg/v-librasil-raw/resolve/main/videos/"
ARTICULATORS = (1, 2, 3)

# nossa glosa → nome do sinal na V-LIBRASIL.
# Os sinais da lista que NÃO estão aqui não existem na base: o grupo grava.
GLOSS_TO_LIBRASIL = {
    "OI": "Oi",
    "SIM": "Sim",
    "NAO": "Não",
    "OBRIGADO": "Obrigado",
    "AJUDA": "Ajudar",
    "BANHEIRO": "Banheiro",
    "AGUA": "Água",
    "DESCULPA": "Desculpa",
    "POR_FAVOR": "Por favor",
}


def fetch(url: str, timeout=120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Vozes em Maos)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []
    for gloss, name in GLOSS_TO_LIBRASIL.items():
        for n in ARTICULATORS:
            dest = OUT_DIR / f"{gloss}__librasil_a{n}.mp4"
            if dest.exists():
                print(f"  já existe: {dest.name}")
                ok += 1
                continue
            url = HF_VIDEOS + urllib.parse.quote(f"{name}_Articulador{n}.mp4")
            try:
                dest.write_bytes(fetch(url))
                print(f"  ok: {dest.name}")
                ok += 1
            except Exception as err:  # sem internet, vídeo que falta na base...
                print(f"  FALHOU: {dest.name} ({err})")
                failed.append(dest.name)

    print(f"\n{ok} vídeos em {OUT_DIR}")
    if failed:
        print(f"{len(failed)} falharam. Rode de novo (os que já baixaram são pulados).")
        sys.exit(1)


if __name__ == "__main__":
    main()
