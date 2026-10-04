/* Sinaliza — reconhecimento de Libras (câmera → texto)

   Pipeline: MediaPipe detecta a mão no navegador (o vídeo NÃO sai do
   dispositivo) → acumulamos os 21 pontos por frame → quando o sinal termina,
   mandamos só esses pontos pra API, que aplica o modelo treinado no
   MINDS-Libras e devolve o sinal reconhecido.

   SEGMENTAÇÃO (quando um sinal começa e termina) é uma heurística: no dataset
   cada vídeo já vinha recortado num sinal só; na webcam o vídeo é contínuo.
   Aqui consideramos que o sinal terminou quando a mão some do quadro por um
   tempo. Funciona pra sinalizar uma palavra por vez, com pausa entre elas —
   não pra conversa fluida. Melhorar isso é um problema em aberto do projeto.
*/
const SEGMENT_END_SILENCE_MS = 700;   // mão fora do quadro por esse tempo = fim do sinal
const MIN_SEGMENT_DETECTED = 8;       // frames com mão mínimos pra valer a pena enviar
const MAX_SEGMENT_FRAMES = 450;       // ~15s a 30fps: força o envio e evita payload gigante
const COORD_DECIMALS = 4;             // arredondar encolhe o JSON sem afetar o modelo

// Ligações entre os 21 pontos da mão, pra desenhar o esqueleto (padrão MediaPipe).
const HAND_BONES = [
  [0,1],[1,2],[2,3],[3,4],        // polegar
  [0,5],[5,6],[6,7],[7,8],        // indicador
  [0,9],[9,10],[10,11],[11,12],   // médio
  [0,13],[13,14],[14,15],[15,16], // anelar
  [0,17],[17,18],[18,19],[19,20], // mindinho
  [5,9],[9,13],[13,17]            // palma
];

const Recognizer = {
  _stream: null,
  _stopped: false,
  _overlayCtx: null,
  _buffer: [],
  _lastHandAt: 0,
  _requestInFlight: false,

  async start(videoEl, { onPhrase, onError, onStatus, overlayEl } = {}) {
    if (!navigator.mediaDevices) {
      onError?.('Câmera não suportada neste navegador.');
      return;
    }

    try {
      this._stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      videoEl.srcObject = this._stream;
      await videoEl.play();
    } catch (err) {
      onError?.('Não foi possível acessar a câmera. Libere a permissão nas configurações do navegador.');
      return;
    }

    try {
      await HandTracking.init();
    } catch (err) {
      console.error('[Recognizer] Falha ao inicializar o HandTracking:', err);
      onError?.('Não foi possível carregar o reconhecimento de mãos. Verifique sua conexão com a internet.');
      return;
    }

    if (overlayEl) {
      overlayEl.hidden = false;
      this._overlayCtx = overlayEl.getContext('2d');
    }

    this._stopped = false;
    this._buffer = [];
    this._lastHandAt = 0;
    this._runLoop(videoEl, { onPhrase, onError, onStatus });
  },

  stop() {
    this._stopped = true;
    this._stream?.getTracks().forEach(track => track.stop());
    this._stream = null;
    this._buffer = [];
  },

  _runLoop(videoEl, callbacks) {
    const tick = () => {
      if (this._stopped) return;

      if (videoEl.readyState >= 2) {
        const detection = HandTracking.detect(videoEl, performance.now());
        this._drawOverlay(videoEl, detection);
        this._collect(detection, callbacks);
      }

      requestAnimationFrame(tick);
    };
    tick();
  },

  _collect({ hands, pose }, callbacks) {
    const now = performance.now();
    const round = points => points && points.map(p => ({
      x: +p.x.toFixed(COORD_DECIMALS),
      y: +p.y.toFixed(COORD_DECIMALS),
      z: +p.z.toFixed(COORD_DECIMALS)
    }));
    const hasHand = Boolean(hands.left || hands.right);

    if (hasHand) {
      this._lastHandAt = now;
      this._buffer.push({
        pose: round(pose) || null,
        hands: { left: round(hands.left) || null, right: round(hands.right) || null }
      });
    } else if (this._buffer.length) {
      this._buffer.push({ pose: round(pose) || null, hands: { left: null, right: null } });
    }

    const detectedCount = this._buffer.filter(f => f.hands.left || f.hands.right).length;
    const silenceMs = now - this._lastHandAt;
    const ended = this._lastHandAt > 0 && silenceMs >= SEGMENT_END_SILENCE_MS;
    const tooLong = this._buffer.length >= MAX_SEGMENT_FRAMES;

    if (!ended && !tooLong) return;

    const segment = this._buffer;
    this._buffer = [];
    this._lastHandAt = 0;

    if (detectedCount >= MIN_SEGMENT_DETECTED) {
      this._predict(segment, callbacks);
    }
  },

  async _predict(frames, { onPhrase, onError, onStatus }) {
    // Uma previsão por vez: se o usuário sinalizar de novo antes da resposta,
    // o segmento novo é descartado em vez de empilhar requisições.
    if (this._requestInFlight) return;
    this._requestInFlight = true;
    onStatus?.('Reconhecendo...');

    try {
      const result = await Api.predictSign(frames);
      if (result.gloss) {
        onPhrase?.(result.gloss, result.confidence);
      } else {
        onStatus?.('Não reconheci esse sinal. Tente de novo.');
      }
    } catch (err) {
      if (err.status === 503) {
        onError?.('O modelo de reconhecimento não está disponível no servidor.');
      } else if (err.status === 422) {
        onStatus?.('Não consegui ver sua mão direito. Tente de novo.');
      } else {
        onError?.(err.message || 'Falha ao reconhecer o sinal.');
      }
    } finally {
      this._requestInFlight = false;
    }
  },

  _drawOverlay(videoEl, { hands, pose }) {
    const ctx = this._overlayCtx;
    if (!ctx) return;
    const canvas = ctx.canvas;

    if (videoEl.videoWidth && canvas.width !== videoEl.videoWidth) {
      canvas.width = videoEl.videoWidth;
      canvas.height = videoEl.videoHeight;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // O canvas tem o tamanho do VÍDEO (ex.: 1280x720), mas é exibido encolhido
    // pela largura do card. Um raio fixo em pixels ficaria minúsculo na tela,
    // então escalamos pelo tamanho do canvas: ~0,9% da largura.
    const unit = canvas.width / 110;

    const dots = (points, color, radius) => {
      if (!points) return;
      ctx.fillStyle = color;
      ctx.strokeStyle = 'rgba(15,23,42,.55)';  // contorno escuro: destaca em fundo claro
      ctx.lineWidth = Math.max(1, unit * 0.22);
      for (const p of points) {
        ctx.beginPath();
        ctx.arc(p.x * canvas.width, p.y * canvas.height, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
    };

    const line = (points, color) => {
      if (!points) return;
      ctx.strokeStyle = color;
      ctx.lineWidth = unit * 0.45;
      ctx.lineCap = 'round';
      for (const [a, b] of HAND_BONES) {
        ctx.beginPath();
        ctx.moveTo(points[a].x * canvas.width, points[a].y * canvas.height);
        ctx.lineTo(points[b].x * canvas.width, points[b].y * canvas.height);
        ctx.stroke();
      }
    };

    // Só os ombros da pose: são o que o modelo usa como referência do corpo.
    if (pose) dots([pose[11], pose[12]].filter(Boolean), '#f59e0b', unit * 1.5);
    line(hands.right, 'rgba(34,197,94,.85)');
    line(hands.left, 'rgba(37,99,235,.85)');
    dots(hands.right, '#22c55e', unit);
    dots(hands.left, '#2563eb', unit);
  }
};
