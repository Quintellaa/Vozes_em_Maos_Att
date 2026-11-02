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
const MIN_SEGMENT_DETECTED = 6;       // frames com mão mínimos pra valer a pena enviar (a 20fps = 0,3s).
                                      // Era 8: sinais rápidos ou de mão difícil de detectar eram
                                      // descartados em silêncio.
const MIN_SEGMENT_HINT = 3;           // com menos que isso, foi só a mão passando: não avisa nada
const MAX_SEGMENT_FRAMES = 450;       // ~15s a 30fps: força o envio e evita payload gigante
const COORD_DECIMALS = 4;             // arredondar encolhe o JSON sem afetar o modelo
const DETECT_FPS = 20;                // quadros analisados por segundo. Rodar o MediaPipe em
                                      // TODO quadro (até 60/s) travava notebooks; o modelo
                                      // reamostra o sinal pra 32 quadros de qualquer jeito.
const MIN_SHOULDER_RATIO = 0.6;       // ombros visíveis em menos que isso do sinal = avisamos pra se afastar
const MAX_SHOULDER_Y_USE = 0.85;      // ombros abaixo disso na imagem = perto demais (igual à gravação)

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

  /* callbacks:
       onPhrase(gloss, confidence, alternatives, word) — sinal reconhecido pela API
       onStatus(msg) / onError(msg)                  — mensagens pra tela
       onFrame(detection) — OPCIONAL. Chamado a cada quadro analisado, com
                            { hands, pose } — a tela de gravação usa pra checar
                            o enquadramento ao vivo.
       onSegment(frames)  — OPCIONAL. Se passado, o sinal capturado vai pra ele
                            em vez de ir pra API. É o que a tela de gravação usa:
                            assim o treino recorta os sinais EXATAMENTE como o
                            reconhecimento recorta na hora de usar. */
  async start(videoEl, { onPhrase, onError, onStatus, onSegment, onFrame, overlayEl } = {}) {
    if (!navigator.mediaDevices) {
      onError?.('Câmera não suportada neste navegador.');
      return;
    }

    try {
      // 640x480 basta pro MediaPipe e é bem mais leve que o 1280x720 padrão de muitas webcams.
      this._stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
      });
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
    this._runLoop(videoEl, { onPhrase, onError, onStatus, onSegment, onFrame });
  },

  stop() {
    this._stopped = true;
    this._stream?.getTracks().forEach(track => track.stop());
    this._stream = null;
    this._buffer = [];
  },

  _runLoop(videoEl, callbacks) {
    let lastDetectAt = 0;
    const tick = () => {
      if (this._stopped) return;

      const now = performance.now();
      if (videoEl.readyState >= 2 && now - lastDetectAt >= 1000 / DETECT_FPS) {
        lastDetectAt = now;
        // Proporção da imagem (largura/altura): celular em pé ≈ 0,75; webcam ≈ 1,33.
        if (videoEl.videoWidth && videoEl.videoHeight) this._aspect = videoEl.videoWidth / videoEl.videoHeight;
        const detection = HandTracking.detect(videoEl, performance.now());
        this._drawOverlay(videoEl, detection);
        callbacks.onFrame?.(detection);
        this._collect(detection, callbacks);
      }

      requestAnimationFrame(tick);
    };
    tick();
  },

  // `now` (ms): na câmera é o relógio; na importação de vídeo é o tempo DO VÍDEO,
  // senão a pausa de fim de sinal seria medida no tempo que o detector demorou.
  _collect({ hands, pose }, callbacks, now = performance.now()) {
    // O MediaPipe dá x como fração da LARGURA e y como fração da ALTURA. Numa
    // imagem que não é quadrada, isso distorce as distâncias — e o mesmo sinal
    // vira números diferentes no celular em pé e na webcam deitada. Multiplicar
    // x pela proporção (largura/altura) põe x e y na mesma escala, então os
    // pontos ficam iguais em qualquer câmera ou orientação. (Os pontos vão
    // pra API e pras gravações já corrigidos: treino e uso sempre iguais.)
    const aspect = this._aspect || 1;
    const round = points => points && points.map(p => ({
      x: +(p.x * aspect).toFixed(COORD_DECIMALS),
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

    if (detectedCount < MIN_SEGMENT_DETECTED) {
      // Antes isso sumia sem nenhuma mensagem e parecia que "o app não reconheceu".
      if (detectedCount >= MIN_SEGMENT_HINT) {
        callbacks.onStatus?.('Vi sua mão por pouco tempo. Faça o sinal um pouco mais devagar e com a mão bem visível.');
      }
      return;
    }

    // O modelo mede tudo em relação aos OMBROS. Se eles não aparecem, o sinal
    // chega "cego" pro modelo e ele chuta. Melhor avisar do que errar calado.
    // (o MediaPipe estima os ombros mesmo fora do quadro; por isso conferimos
    // se as coordenadas, que vão de 0 a 1, estão DENTRO da imagem)
    const inFrame = p => p && p.x > 0 && p.x < aspect && p.y > 0 && p.y < 1; // x vai de 0 até a proporção
    const withShoulders = segment.filter(f => f.pose && inFrame(f.pose[11]) && inFrame(f.pose[12])).length;
    // Ombros colados no rodapé = pessoa perto demais: as mãos saem do quadro
    // durante o sinal. Mesma regra da tela de gravação (treino e uso iguais).
    const withPose = segment.filter(f => f.pose);
    const shoulderY = withPose.length
      ? withPose.reduce((sum, f) => sum + (f.pose[11].y + f.pose[12].y) / 2, 0) / withPose.length
      : 1;
    if (withShoulders / segment.length < MIN_SHOULDER_RATIO || shoulderY > MAX_SHOULDER_Y_USE) {
      callbacks.onStatus?.('Afaste-se: ombros e mãos precisam aparecer.');
      return;
    }

    if (callbacks.onSegment) callbacks.onSegment(segment);
    else this._predict(segment, callbacks);
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
        onPhrase?.(result.gloss, result.confidence, result.alternatives, result.word || glossToWord(result.gloss));
      } else {
        // Mostrar os palpites ajuda a entender o erro (e a ajustar o sinal).
        const guesses = (result.alternatives || [])
          .map(a => `${a.word || glossToWord(a.gloss)} ${Math.round(a.confidence * 100)}%`).join(', ');
        onStatus?.(guesses ? `Não tive certeza. Palpites: ${guesses}` : 'Não reconheci esse sinal. Tente de novo.');
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
