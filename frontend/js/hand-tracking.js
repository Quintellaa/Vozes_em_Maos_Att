/* Sinaliza — wrapper do MediaPipe Hand Landmarker
   Isola a API específica do MediaPipe neste arquivo só: o resto do app chama
   apenas HandTracking.init() e HandTracking.detect(video, timestamp).

   vision_bundle.mjs é um módulo ES de verdade (tem `export` dentro) — por
   isso usamos import() dinâmico aqui dentro, em vez de uma tag <script src>
   separada no HTML. Isso funciona mesmo este arquivo sendo um script comum
   (não type="module"): import() dinâmico é permitido em qualquer script.
*/
const MEDIAPIPE_VERSION = '0.10.35'; // versão fixa, mesmo raciocínio do three.js@0.160.0
const MEDIAPIPE_BUNDLE_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MEDIAPIPE_VERSION}/vision_bundle.mjs`;
const MEDIAPIPE_WASM_URL = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MEDIAPIPE_VERSION}/wasm`;
const HAND_LANDMARKER_MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task';
const POSE_LANDMARKER_MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';

// Limiares de confiança do MediaPipe. O padrão (0,5) descarta mãos "difíceis" —
// punho fechado, dedos sobrepostos, mão borrada pelo movimento — que são justamente
// as de vários sinais (sim, não, obrigado...). Com 0,4 elas passam a ser detectadas.
// O backend (libras_features.py) funde detecções duplicadas, então o risco de
// aparecer uma mão a mais é coberto lá.
const MIN_HAND_CONFIDENCE = 0.4;
const MIN_POSE_CONFIDENCE = 0.4;

const HandTracking = {
  _hands: null,
  _pose: null,

  async init() {
    if (this._hands) return; // já inicializado — evita recarregar os modelos
    const { FilesetResolver, HandLandmarker, PoseLandmarker } = await import(MEDIAPIPE_BUNDLE_URL);
    const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_URL);

    // Tenta rodar na placa de vídeo (GPU), que é bem mais rápida; se o
    // navegador não suportar, cai pro processador (CPU) sem quebrar.
    const create = async (Task, modelUrl, extra) => {
      for (const delegate of ['GPU', 'CPU']) {
        try {
          return await Task.createFromOptions(vision, {
            baseOptions: { modelAssetPath: modelUrl, delegate },
            runningMode: 'video',
            ...extra
          });
        } catch (err) {
          if (delegate === 'CPU') throw err;
          console.warn(`[HandTracking] GPU indisponível, usando CPU:`, err);
        }
      }
    };

    // numHands: 2 porque vários sinais de Libras usam as duas mãos.
    this._hands = await create(HandLandmarker, HAND_LANDMARKER_MODEL_URL, {
      numHands: 2,
      minHandDetectionConfidence: MIN_HAND_CONFIDENCE,
      minHandPresenceConfidence: MIN_HAND_CONFIDENCE,
      minTrackingConfidence: MIN_HAND_CONFIDENCE
    });
    // A pose dá os ombros, que servem de referência pra saber ONDE no corpo o
    // sinal acontece — informação essencial em Libras.
    this._pose = await create(PoseLandmarker, POSE_LANDMARKER_MODEL_URL, {
      numPoses: 1,
      minPoseDetectionConfidence: MIN_POSE_CONFIDENCE,
      minPosePresenceConfidence: MIN_POSE_CONFIDENCE,
      minTrackingConfidence: MIN_POSE_CONFIDENCE
    });
  },

  // Retorna { hands: {left, right}, pose } do frame atual.
  // Cada campo é uma lista de pontos {x,y,z} normalizados (0–1) ou null.
  detect(videoEl, timestampMs) {
    if (!this._hands) return { hands: { left: null, right: null }, pose: null };

    const handResult = this._hands.detectForVideo(videoEl, timestampMs);
    const hands = { left: null, right: null };
    const found = handResult.landmarks || [];
    // O MediaPipe decide esquerda/direita assumindo imagem espelhada (selfie).
    // O rótulo pode não bater com a mão real da pessoa — e às vezes dá o MESMO
    // rótulo pras duas mãos. Antes, a segunda era jogada fora (perdendo mão de
    // sinais com as duas mãos). Agora ela vai pro outro lado, que está livre.
    // O que importa é ser o MESMO critério no treino e no uso, e é.
    const labelOf = i => {
      const l = handResult.handednesses?.[i]?.[0]?.categoryName?.toLowerCase();
      return l === 'left' || l === 'right' ? l : null;
    };
    const order = found.map((_, i) => i);
    if (found.length === 2 && labelOf(0) && labelOf(0) === labelOf(1)) {
      // rótulos iguais: decide pela posição (a mão mais à esquerda da imagem fica com "right")
      order.sort((a, b) => found[a][0].x - found[b][0].x);
      hands.right = found[order[0]];
      hands.left = found[order[1]];
    } else {
      order.forEach(i => {
        const label = labelOf(i) || (hands.right ? 'left' : 'right');
        const slot = hands[label] ? (label === 'left' ? 'right' : 'left') : label;
        if (!hands[slot]) hands[slot] = found[i];
      });
    }

    const poseResult = this._pose?.detectForVideo(videoEl, timestampMs);
    const pose = poseResult?.landmarks?.[0] ?? null;

    return { hands, pose };
  }
};
