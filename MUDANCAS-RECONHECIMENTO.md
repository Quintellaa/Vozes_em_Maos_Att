# Melhorias no reconhecimento de sinais (22/10/2026)

## O que as gravações reais mostraram
Analisei as 15 gravações em `dados/gravacoes/` (oi, sim, não). Em **todos** os quadros em que o
detector viu "duas mãos", era a **mesma mão detectada duas vezes** (uma como esquerda, outra como
direita). Além disso, o rótulo esquerda/direita **piscava** por 1–3 quadros no começo de vários sinais
(ex.: `R L L B R R R...`). O extrator antigo (v2) tratava isso como mãos diferentes e como mão que
sumiu, então o sinal chegava ao modelo "sujo".

## O que mudou

### 1. `backend/app/libras_features.py` — novas características `pose-hands-v3` (principal)
- **Mãos fantasma fundidas:** duas detecções praticamente no mesmo lugar viram uma mão só.
- **Mãos seguidas pela posição**, não pelo rótulo esquerda/direita do MediaPipe. O rótulo só decide
  se o clipe inteiro é espelhado (canhoto = destro).
- **Quadros perdidos** (1 a 4 seguidos) no meio do sinal são preenchidos por interpolação.
- **Novas medidas da mão:** dedos dobrados, distância entre pontas dos dedos, orientação da palma,
  direção da mão, ponta dos dedos/indicador em relação ao nariz, posição de uma mão em relação à outra.
  Tamanho da palma agora usa 4 distâncias em 3D (antes 1 só, que ia a zero quando a mão aponta pra câmera).
- **Resumo do clipe** (médias, variação, caminho percorrido) que não muda com a velocidade do sinal.
- Ombros/nariz suavizados (mediana de 5 quadros) pra reduzir o tremido do detector de pose.
- As versões `hand-v1`, `pose-hands-v1` e `pose-hands-v2` continuam iguais: o modelo MINDS (20 sinais)
  segue funcionando. Cada modelo usa a versão com que foi treinado.

### 2. `backend/app/routers/recognition.py` — previsão mais estável
- Pra modelos v3, além do recorte original a API olha mais 3 recortes (cortando ~12% do começo, do fim, ou dos dois) e faz a **média das probabilidades**. Se o recorte pegou um pedaço de mão subindo/descendo, isso não derruba mais o resultado.

### 3. `frontend/js/hand-tracking.js` — detecção
- **Bug corrigido:** quando o MediaPipe dava o mesmo rótulo às duas mãos, a segunda era **descartada**
  (perdia metade dos sinais de duas mãos). Agora vai pro outro lado.
- Limiares de confiança do MediaPipe de 0,5 (padrão) para **0,4** (mãos e pose): passa a detectar
  punho fechado, dedos sobrepostos e mão borrada pelo movimento.

### 4. `frontend/js/recognizer.js` — captura
- Mínimo de quadros com mão: **8 → 6**. Antes, sinais rápidos eram descartados em silêncio.
- Quando o sinal é curto demais, agora aparece o aviso *"Vi sua mão por pouco tempo. Faça o sinal um pouco mais devagar…"*
  em vez de não acontecer nada.

### 5. `tools/train_and_export.py` — treino
- Aumento de dados também simula **rótulo piscando** e **mão fantasma** (os defeitos reais), e mais quadros perdidos (8% → 10%).
- Variações por gravação: 5 → 8.
- Novo algoritmo candidato: **Extra Trees** (além de RF, SVM, KNN e regressão logística).

### 6. Modelo e testes
- `backend/models/libras_grupo.joblib` **retreinado** com a v3 (mesmos 15 clipes). O anterior ficou como `libras_grupo_antigo_v2.joblib`.
- Testes novos em `backend/tests/` (mão fantasma, rótulo piscando, buraco curto, canhoto, formato antigo, aumento de dados).

## O que NÃO dá pra resolver só com código
- O modelo atual só conhece **3 sinais** (oi, sim, não). Qualquer outro sinal vai ser confundido com um desses
  ou não reconhecido. Pra reconhecer mais sinais é preciso **gravar** (ver `STATUS-17-10.md` e `tools/README.md`)
  e rodar `tools/train_and_export.py`.
- Com 1 pessoa gravando, a acurácia do relatório é otimista. Grave com 2+ pessoas.

## Como aplicar
1. `cd backend`, e reinicie a API (Ctrl+C e `py -3.14 -m uvicorn app.main:app --reload`).
2. Recarregue o `tradutor.html` com Ctrl+F5 (pra limpar o JavaScript antigo do cache).
3. Gravou mais sinais? `py -3.14 tools/train_and_export.py` na raiz e reinicie a API.
