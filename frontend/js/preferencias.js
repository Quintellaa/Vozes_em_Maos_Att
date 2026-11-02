/* Sinaliza — preferências do usuário (Acessibilidade e Notificações)
   Carregado em TODAS as páginas, logo depois de storage.js, para que alto
   contraste, tamanho do texto etc. valham no app inteiro e não só no perfil.
   As escolhas ficam salvas neste aparelho (Storage → localStorage).
*/
const PREFS_KEY = 'prefs';

const PREFS_PADRAO = {
  // Acessibilidade
  altoContraste: false,
  tamanhoTexto: 'normal',      // 'normal' | 'grande' | 'maior'
  reduzirAnimacoes: false,
  falarSinais: true,           // fala em voz alta o sinal reconhecido no Tradutor
  velocidadeVoz: 1,            // 0.8 | 1 | 1.25
  // Notificações
  somSinal: false,             // "bip" quando um sinal é reconhecido
  vibrarSinal: false,          // vibração (celular) quando um sinal é reconhecido
  lembrete: false,             // lembrete diário para praticar
  lembreteHora: '19:00'
};

const Prefs = {
  todas() {
    return { ...PREFS_PADRAO, ...(Storage.get(PREFS_KEY, {}) || {}) };
  },

  get(chave) {
    return this.todas()[chave];
  },

  set(chave, valor) {
    const prefs = { ...this.todas(), [chave]: valor };
    const ok = Storage.set(PREFS_KEY, prefs);
    this.aplicar(prefs);
    if (chave.startsWith('lembrete')) this.agendarLembrete();
    return ok;
  },

  /** Aplica as opções visuais na página (atributos no <html>, estilos em style.css). */
  aplicar(prefs = this.todas()) {
    const html = document.documentElement;
    html.toggleAttribute('data-alto-contraste', !!prefs.altoContraste);
    html.toggleAttribute('data-reduzir-animacoes', !!prefs.reduzirAnimacoes);
    if (prefs.tamanhoTexto && prefs.tamanhoTexto !== 'normal') html.dataset.texto = prefs.tamanhoTexto;
    else delete html.dataset.texto;
  },

  /** Chamado pelo Tradutor sempre que um sinal é reconhecido. */
  avisarSinal() {
    const prefs = this.todas();
    if (prefs.somSinal) this.bip();
    if (prefs.vibrarSinal) this.vibrar();
  },

  /** Vibração curta. Android: navigator.vibrate. iPhone não tem essa função, mas no iOS 18+
      marcar um <input switch> faz o aparelho dar um "toque" — usamos um escondido pra isso. */
  vibrar() {
    if (navigator.vibrate) return navigator.vibrate(80);
    const label = document.createElement('label');
    label.setAttribute('aria-hidden', 'true');
    label.style.display = 'none';
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.setAttribute('switch', '');
    label.appendChild(input);
    document.head.appendChild(label);
    label.click();
    label.remove();
    return true;
  },

  _audio: null,
  /** Prepara o áudio. No iPhone ele só destrava dentro de um toque na tela, e o modo
      silencioso cala o som da página — o tipo 'playback' faz o bip tocar mesmo assim. */
  _audioPronto() {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    if (navigator.audioSession) {
      try { navigator.audioSession.type = 'playback'; } catch (err) { /* navegador sem suporte */ }
    }
    this._audio = this._audio || new Ctx();
    if (this._audio.state !== 'running') this._audio.resume().catch(() => {});
    return this._audio;
  },

  bip() {
    try {
      const ctx = this._audioPronto();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.0001, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.25, ctx.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.18);
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.2);
    } catch (err) {
      console.warn('[Prefs] Não foi possível tocar o som:', err);
    }
  },

  // ---------- Notificações do navegador ----------
  notificacoesSuportadas: 'Notification' in window,

  statusNotificacao() {
    return this.notificacoesSuportadas ? Notification.permission : 'unsupported'; // granted | denied | default
  },

  async pedirPermissaoNotificacao() {
    if (!this.notificacoesSuportadas) return 'unsupported';
    try { return await Notification.requestPermission(); } catch (err) { return Notification.permission; }
  },

  notificar(titulo, corpo) {
    if (this.statusNotificacao() !== 'granted') return false;
    try {
      new Notification(titulo, { body: corpo, lang: 'pt-BR', tag: 'sinaliza' });
      return true;
    } catch (err) {
      return false; // alguns celulares só aceitam notificação via service worker
    }
  },

  // ---------- Lembrete diário ----------
  // Sem servidor de push, o lembrete só aparece enquanto alguma tela do Sinaliza
  // estiver aberta no navegador (avisamos isso na tela de Notificações).
  _timerLembrete: null,
  agendarLembrete() {
    clearTimeout(this._timerLembrete);
    const prefs = this.todas();
    if (!prefs.lembrete || this.statusNotificacao() !== 'granted') return;

    const [h, m] = String(prefs.lembreteHora || '19:00').split(':').map(Number);
    const agora = new Date();
    const alvo = new Date(agora);
    alvo.setHours(h || 0, m || 0, 0, 0);
    const hoje = agora.toDateString();
    if (alvo <= agora) {
      // Já passou do horário hoje: se foi há pouco (até 3h) e ainda não lembrou, lembra agora; senão, amanhã.
      const atrasoMs = agora - alvo;
      if (atrasoMs < 3 * 3600e3 && Storage.get('lembreteUltimo') !== hoje) return this._dispararLembrete();
      alvo.setDate(alvo.getDate() + 1);
    }
    this._timerLembrete = setTimeout(() => this._dispararLembrete(), alvo - agora);
  },

  _dispararLembrete() {
    Storage.set('lembreteUltimo', new Date().toDateString());
    this.notificar('Hora de praticar Libras ✋', 'Que tal treinar alguns sinais no Vozes em Mãos hoje?');
    this.agendarLembrete();
  }
};

Prefs.aplicar();
Prefs.agendarLembrete();

// O bip do Tradutor toca sem ninguém tocar na tela, mas o iPhone só libera o áudio dentro
// de um toque. Com o som ligado, aproveitamos o primeiro toque em qualquer lugar da página.
function destravarAudio() {
  if (!Prefs.get('somSinal')) return;
  Prefs._audioPronto();
  ['touchend', 'click'].forEach(ev => document.removeEventListener(ev, destravarAudio, true));
}
['touchend', 'click'].forEach(ev => document.addEventListener(ev, destravarAudio, true));
