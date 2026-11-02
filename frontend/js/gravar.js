/* Sinaliza — tela de gravação de sinais (gera os dados de TREINO do modelo)

   Fluxo: a pessoa escolhe o sinal → faz o sinal → abaixa as mãos → conta uma
   amostra → repete. No total, baixa um arquivo .json com todas as amostras.

   O recorte de cada amostra é feito pelo MESMO código do reconhecimento
   (Recognizer, com onSegment). Isso é essencial: se o treino recortasse os
   sinais de um jeito e o uso de outro, o modelo veria coisas diferentes nas
   duas situações e erraria.

   Só os PONTOS (mãos + corpo) são salvos. Nenhuma imagem ou vídeo sai da câmera.
*/
const RECORDING_FORMAT = 'sinaliza-recording-v1';

// Controle de qualidade das amostras. Gravação ruim ensina o modelo errado, e é
// bem mais fácil regravar na hora do que descobrir no treino.
const MAX_SHOULDER_Y = 0.85;   // ombros abaixo disso (0 = topo, 1 = rodapé) = perto demais
const MIN_HAND_RATIO = 0.5;    // a mão precisa aparecer em pelo menos metade do sinal

// Avalia uma amostra. Devolve null se estiver boa, ou o motivo pra descartar.
function clipProblem(frames) {
  const withPose = frames.filter(f => f.pose);
  const shoulderY = withPose.length
    ? withPose.reduce((sum, f) => sum + (f.pose[11].y + f.pose[12].y) / 2, 0) / withPose.length
    : 1;
  const handRatio = frames.filter(f => f.hands.left || f.hands.right).length / frames.length;

  if (shoulderY > MAX_SHOULDER_Y) return 'Você está perto demais: afaste-se até os ombros ficarem bem visíveis.';
  if (handRatio < MIN_HAND_RATIO) return 'A mão saiu da câmera durante o sinal. Faça o sinal mais pra cima, dentro do quadro.';
  return null;
}

pages.gravar = function () {
  const signerEl = $('#signer');
  const signEl = $('#sign');
  const repsEl = $('#reps');
  const countEl = $('#count');
  const statusEl = $('#status');
  const undoBtn = $('#undo');
  const saveBtn = $('#save');
  const startBtn = $('#startCam');

  let clips = [];          // amostras do sinal atual ainda NÃO salvas
  let cameraOn = false;
  let lastFramingAt = 0;
  const savedCount = {};   // gloss → amostras já salvas nesta sessão

  // ---- formulário ----
  signEl.innerHTML = SIGNS_TO_RECORD
    .map(s => `<option value="${escapeHtml(s.gloss)}">${escapeHtml(s.word)}</option>`).join('');
  signerEl.value = Storage.get('recSigner', '');
  repsEl.value = DEFAULT_REPETITIONS;

  const currentSign = () => SIGNS_TO_RECORD.find(s => s.gloss === signEl.value);
  const target = () => Math.max(1, parseInt(repsEl.value, 10) || DEFAULT_REPETITIONS);
  // Nome vira parte do arquivo e identifica a pessoa no treino: só letras/números.
  const signerId = () => normalizeId(signerEl.value);

  function normalizeId(text) {
    return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  }

  function render() {
    countEl.textContent = `${clips.length} / ${target()}`;
    undoBtn.disabled = clips.length === 0;
    saveBtn.disabled = clips.length === 0;
    const done = Object.entries(savedCount)
      .map(([gloss, n]) => `${SIGNS_TO_RECORD.find(s => s.gloss === gloss)?.word ?? gloss}: ${n}`);
    $('#sessionSummary').textContent = done.length ? `Salvos nesta sessão — ${done.join(' · ')}` : '';
  }

  function flash() {
    countEl.classList.remove('ok');
    void countEl.offsetWidth; // reinicia a animação
    countEl.classList.add('ok');
  }

  // ---- salvar ----
  function save() {
    if (!clips.length) return;
    const sign = currentSign();
    const now = new Date();
    const payload = {
      format: RECORDING_FORMAT,
      signer: signerId(),
      gloss: sign.gloss,
      word: sign.word,
      detect_fps: DETECT_FPS,
      // x já vem multiplicado pela proporção da imagem (ver recognizer.js), o que
      // deixa gravações de celular e de webcam compatíveis entre si.
      coord_space: 'aspect-v1',
      aspect: +(Recognizer._aspect || 1).toFixed(3),
      created_at: now.toISOString(),
      user_agent: navigator.userAgent,
      clips
    };
    const stamp = now.toISOString().slice(0, 16).replace(/[:T]/g, '-');
    const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `sinal_${sign.gloss}_${signerId()}_${stamp}.json`;
    link.click();
    URL.revokeObjectURL(link.href);

    savedCount[sign.gloss] = (savedCount[sign.gloss] || 0) + clips.length;
    toast(`${clips.length} amostras de "${sign.word}" salvas em Downloads.`);
    statusEl.textContent = 'Arquivo salvo! Escolha o próximo sinal (ou continue gravando este).';
    clips = [];
    render();
  }

  saveBtn.onclick = save;

  undoBtn.onclick = () => {
    clips.pop();
    statusEl.textContent = 'Última amostra descartada.';
    render();
  };

  // Trocar de sinal com amostras pendentes: salva antes, pra não misturar nem perder.
  let previousSign = signEl.value;
  signEl.onchange = () => {
    if (clips.length) {
      const chosen = signEl.value;
      signEl.value = previousSign;
      save();
      signEl.value = chosen;
    }
    previousSign = signEl.value;
    showRefWord();
    statusEl.textContent = `Agora: "${currentSign().word}". Faça o sinal e abaixe as mãos.`;
    render();
  };

  // ---- referência: o avatar do VLibras mostra como se faz o sinal escolhido ----
  const showRefWord = () => { $('#refPlay').textContent = `Mostrar o sinal de "${currentSign().word}"`; };
  showRefWord();
  LibrasPlayer.embedIn($('#refStage'));
  LibrasPlayer.start();
  // O widget do VLibras cria uma janela própria que fica por cima da página.
  // Ela só aparece com "Ver como se faz o sinal" aberto; fechado, some de vez
  // e libera a câmera. Começar a gravar também fecha a referência.
  const refBox = $('#refBox');
  const syncAvatar = () => {
    const host = document.getElementById('vlibras-app-root');
    if (host) host.style.display = refBox.open ? '' : 'none';
  };
  refBox.addEventListener('toggle', syncAvatar);
  setInterval(syncAvatar, 300); // o widget cria a janela depois de carregar
  $('#startCam').addEventListener('click', () => { refBox.open = false; syncAvatar(); });
  $('#refPlay').onclick = async () => {
    if (!LibrasPlayer.ready()) toast('Carregando o avatar do VLibras (a 1ª vez demora)...');
    try {
      await LibrasPlayer.sign(currentSign().word);
    } catch (err) {
      toast(err.message);
    }
  };

  repsEl.oninput = render;
  signerEl.oninput = () => Storage.set('recSigner', signerEl.value);

  window.addEventListener('beforeunload', e => {
    if (clips.length) { e.preventDefault(); e.returnValue = ''; }
  });

  // ---- câmera ----
  startBtn.onclick = async () => {
    if (!signerId()) {
      toast('Preencha seu nome primeiro.');
      signerEl.focus();
      return;
    }
    if (cameraOn) return;
    cameraOn = true;
    startBtn.disabled = true;
    statusEl.textContent = 'Carregando a câmera e o detector de mãos...';

    await Recognizer.start($('#video'), {
      overlayEl: $('#handOverlay'),
      onStatus: msg => { statusEl.textContent = msg; },
      onError: msg => {
        statusEl.textContent = msg;
        cameraOn = false;
        startBtn.disabled = false;
      },
      onFrame({ pose }) {
        // Aviso de enquadramento ao vivo (atualiza no máximo 2x por segundo)
        const now = performance.now();
        if (now - lastFramingAt < 500) return;
        lastFramingAt = now;
        const framingEl = $('#framing');
        if (!pose) {
          framingEl.textContent = 'Não estou vendo você';
          framingEl.className = 'rec-framing bad';
        } else if ((pose[11].y + pose[12].y) / 2 > MAX_SHOULDER_Y) {
          framingEl.textContent = 'Muito perto: afaste-se';
          framingEl.className = 'rec-framing bad';
        } else {
          framingEl.textContent = 'Enquadramento bom';
          framingEl.className = 'rec-framing ok';
        }
      },
      onSegment(frames) {
        if (clips.length >= target()) return; // já completou; esperando salvar
        const problem = clipProblem(frames);
        if (problem) {
          statusEl.textContent = `Amostra descartada. ${problem}`;
          return;
        }
        clips.push({ recorded_at: new Date().toISOString(), frames });
        flash();
        const left = target() - clips.length;
        statusEl.textContent = left > 0
          ? `Amostra ${clips.length} gravada. Faltam ${left}.`
          : 'Pronto! Salvando o arquivo...';
        render();
        if (left <= 0) save();
      }
    });

    if (cameraOn) {
      $('#framing').hidden = false;
      statusEl.textContent = `Gravando "${currentSign().word}". Faça o sinal e abaixe as mãos.`;
      startBtn.textContent = 'Câmera ligada';
    }
  };

  // ---- importar vídeos gravados no celular ----
  // O vídeo é "tocado" num player escondido atrás da câmera e cada quadro passa
  // pelo MESMO caminho da câmera ao vivo (detector → recorte → controle de
  // qualidade). Assim, gravações de vídeo e ao vivo saem idênticas.
  const importStatus = $('#importStatus');

  async function processVideo(file) {
    if (cameraOn) {
      Recognizer.stop();
      cameraOn = false;
      startBtn.disabled = false;
      startBtn.textContent = 'Iniciar câmera';
    }
    await HandTracking.init();

    // Cada arquivo ganha um <video> SÓ DELE, posto no lugar do da câmera enquanto
    // é analisado. Reaproveitar o mesmo player entre arquivos misturava eventos e
    // quadros de um vídeo com o seguinte (uns analisados 2x, outros nenhuma).
    const cameraVideo = $('#video');
    const video = document.createElement('video');
    video.className = cameraVideo.className;
    video.muted = true;
    video.playsInline = true;
    cameraVideo.hidden = true;
    cameraVideo.after(video);
    const url = URL.createObjectURL(file);
    try {
      return await analyzeVideo(file, video, url);
    } finally {
      video.remove();
      cameraVideo.hidden = false;
      URL.revokeObjectURL(url);
    }
  }

  async function analyzeVideo(file, video, url) {
    video.src = url;
    await new Promise((resolve, reject) => {
      video.onloadeddata = resolve;
      video.onerror = () => reject(new Error(`Não consegui abrir "${file.name}". Tente outro formato (MP4).`));
    });
    if (!video.videoWidth || !video.videoHeight) {
      throw new Error(`"${file.name}": o navegador abriu o arquivo mas não consegue mostrar a imagem (formato HEVC?). No iPhone: Ajustes → Câmera → Formatos → "Mais Compatível". Ou converta pra MP4 (H.264).`);
    }

    // mesma correção de proporção da câmera ao vivo (celular em pé ≈ 0,56–0,75)
    Recognizer._aspect = video.videoWidth / video.videoHeight;
    Recognizer._buffer = [];
    Recognizer._lastHandAt = 0;
    const overlay = $('#handOverlay');
    overlay.hidden = false;
    Recognizer._overlayCtx = overlay.getContext('2d');

    let accepted = 0, rejected = 0;
    const reasons = {};
    // Diagnóstico: quando nada é aproveitado, isso diz POR QUÊ (mão não detectada,
    // ombros fora da imagem...), em vez de só "nenhuma repetição".
    const diag = { frames: 0, hand: 0, pose: 0, shoulders: 0 };
    const countReason = msg => { rejected++; reasons[msg] = (reasons[msg] || 0) + 1; };
    const callbacks = {
      // o Recognizer descarta aqui repetições com os ombros fora da imagem
      onStatus: msg => countReason(msg.replace('Afaste-se: ', 'ombros fora da imagem — ')),
      onSegment(frames) {
        const problem = clipProblem(frames);
        if (problem) return countReason(problem);
        clips.push({ recorded_at: new Date().toISOString(), source: 'video', file: file.name, frames });
        accepted++;
        flash();
        render();
      }
    };

    // Avança o vídeo quadro a quadro (DETECT_FPS por segundo de vídeo), sem tocar.
    // Tocando, o vídeo corria em tempo real enquanto o detector demorava em cada
    // quadro (ainda mais em 1080p), e um sinal curto acabava com 1 ou 2 quadros
    // analisados — descartado por "poucos quadros com mão". É mais lento, mas
    // analisa sempre os mesmos quadros, em qualquer computador.
    // O relógio passado pro _collect é o tempo do vídeo (+1s, porque 0 = "sem mão ainda").
    const clock = t => 1000 + t * 1000;
    const seekTo = t => new Promise((resolve, reject) => {
      if (Math.abs(video.currentTime - t) < 1e-3) return resolve(); // já está nesse quadro
      video.onseeked = resolve;
      video.onerror = () => reject(new Error(`"${file.name}": erro ao ler o vídeo.`));
      video.currentTime = t;
    });
    let t = 0;
    for (; t < video.duration; t += 1 / DETECT_FPS) {
      await seekTo(t);
      const detection = HandTracking.detect(video, performance.now());
      diag.frames++;
      if (detection.hands.left || detection.hands.right) diag.hand++;
      if (detection.pose) {
        diag.pose++;
        const ok = p => p && p.x > 0 && p.x < 1 && p.y > 0 && p.y < 1;
        if (ok(detection.pose[11]) && ok(detection.pose[12])) diag.shoulders++;
      }
      Recognizer._drawOverlay(video, detection);
      Recognizer._collect(detection, callbacks, clock(t));
      importStatus.textContent = `Processando "${file.name}": ${Math.round(t)}s de ${Math.round(video.duration)}s — ${accepted} repetições boas até agora.`;
    }

    // fecha a última repetição, se o vídeo acabou com a mão ainda na imagem
    const empty = { hands: { left: null, right: null }, pose: null };
    for (let extra = 0; extra * 1000 / DETECT_FPS <= SEGMENT_END_SILENCE_MS + 100; extra++) {
      Recognizer._collect(empty, callbacks, clock(t + extra / DETECT_FPS));
    }
    return { accepted, rejected, reasons, diag };
  }

  // Vídeos baixados por tools/baixar_librasil.py se chamam "<GLOSA>__<pessoa>.mp4":
  // o sinal e a pessoa saem do nome do arquivo, e cada vídeo vira um .json.
  const fromFileName = file => {
    const m = file.name.match(/^([A-Z_]+)__([a-z0-9_]+)\.mp4$/);
    return m && SIGNS_TO_RECORD.some(s => s.gloss === m[1]) ? { gloss: m[1], signer: m[2] } : null;
  };

  $('#videoFiles').onchange = async event => {
    const files = [...event.target.files];
    event.target.value = ''; // permite escolher o mesmo arquivo de novo
    if (!files.length) return;
    if (!signerId() && !files.every(fromFileName)) {
      toast('Preencha seu nome primeiro.');
      signerEl.focus();
      return;
    }
    if (clips.length) save(); // não mistura com amostras pendentes de outra origem

    const typed = { sign: signEl.value, signer: signerEl.value };
    const lines = [];
    for (const file of files) {
      const named = fromFileName(file);
      if (named) {
        signEl.value = named.gloss;
        signerEl.value = named.signer;
      } else {
        signEl.value = typed.sign;
        signerEl.value = typed.signer;
      }
      try {
        const r = await processVideo(file);
        if (named && clips.length) save();
        const why = Object.entries(r.reasons).map(([m, n]) => `${n}× ${m}`).join(' ');
        const pct = n => r.diag.frames ? Math.round(100 * n / r.diag.frames) : 0;
        lines.push(`"${file.name}": ${r.accepted} repetições boas` + (r.rejected ? `, ${r.rejected} descartadas (${why})` : '') + '.'
          + ` [quadros analisados: ${r.diag.frames}; mão vista em ${pct(r.diag.hand)}%; corpo em ${pct(r.diag.pose)}%; os 2 ombros dentro da imagem em ${pct(r.diag.shoulders)}%]`);
      } catch (err) {
        lines.push(err.message);
      }
    }
    signEl.value = typed.sign;
    signerEl.value = typed.signer;
    previousSign = signEl.value;
    importStatus.textContent = lines.join(' ');
    if (clips.length) {
      save();
    } else if (files.some(fromFileName)) {
      statusEl.textContent = 'Importação terminada. Confira abaixo do botão "Importar vídeo" quantas repetições cada vídeo deu.';
    } else {
      statusEl.textContent = 'Nenhuma repetição aproveitada. Veja o motivo logo abaixo do botão "Importar vídeo".';
      $('#importBox')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  render();
};
