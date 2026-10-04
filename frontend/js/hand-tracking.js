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

const HandTracking = {
  _hands: null,
  _pose: null,

  async init() {
    if (this._hands) return; // já inicializado — evita recarregar os modelos
    const { FilesetResolver, HandLandmarker, PoseLandmarker } = await import(MEDIAPIPE_BUNDLE_URL);
    const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_URL);

    // numHands: 2 porque vários sinais de Libras usam as duas mãos.
    this._hands = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: HAND_LANDMARKER_MODEL_URL },
      runningMode: 'video',
      numHands: 2
    });
    // A pose dá os ombros, que servem de referência pra saber ONDE no corpo o
    // sinal acontece — informação essencial em Libras.
    this._pose = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: POSE_LANDMARKER_MODEL_URL },
      runningMode: 'video',
      numPoses: 1
    });
  },

  // Retorna { hands: {left, right}, pose } do frame atual.
  // Cada campo é uma lista de pontos {x,y,z} normalizados (0–1) ou null.
  detect(videoEl, timestampMs) {
    if (!this._hands) return { hands: { left: null, right: null }, pose: null };

    const handResult = this._hands.detectForVideo(videoEl, timestampMs);
    const hands = { left: null, right: null };
    (handResult.landmarks || []).forEach((points, i) => {
      // O MediaPipe decide esquerda/direita assumindo imagem espelhada (selfie).
      // O rótulo pode não bater com a mão real da pessoa — o que importa é ser
      // o MESMO critério usado no treino, e é.
      const label = handResult.handednesses?.[i]?.[0]?.categoryName?.toLowerCase();
      if ((label === 'left' || label === 'right') && !hands[label]) hands[label] = points;
    });

    const poseResult = this._pose?.detectForVideo(videoEl, timestampMs);
    const pose = poseResult?.landmarks?.[0] ?? null;

    return { hands, pose };
  }
};
