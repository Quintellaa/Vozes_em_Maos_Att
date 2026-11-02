/* Sinaliza — texto → Libras com o VLibras (avatar oficial do Governo Federal)

   POR QUE VLIBRAS: o avatar próprio que tínhamos conhecia só 20 palavras e
   mexia só os braços. O VLibras é gratuito, de código aberto, tem dicionário
   de milhares de sinais (com configuração de mão e expressão facial) e foi
   construído com a comunidade surda. Usar a ferramenta oficial pra esse lado
   deixa o grupo focado no lado difícil: reconhecer Libras pela câmera.

   COMO FUNCIONA (conferido no código-fonte do widget:
   github.com/spbgovbr-vlibras/vlibras-web-browsers):
     1. window.VLibrasWidget.open() abre o avatar (carrega o player 3D);
     2. quando o player termina de carregar, o widget publica
        window.vlibras.translateAndPlay(texto) — traduz pra glosa e sinaliza.
        (versões antigas publicavam window.plugin.translate, que também aceitamos)

   AVATAR DENTRO DO NOSSO CARD: o widget foi feito pra flutuar no canto da
   tela. Mover a janela dele de lugar no HTML recarregaria o avatar (ele roda
   num iframe), então fazemos diferente: a janela continua onde o widget cria,
   mas a gente a posiciona EXATAMENTE em cima de uma área do nosso card
   (`embedIn(elemento)`), do mesmo tamanho, e esconde o cabeçalho, a barra de
   controles e o botão flutuante dele. O widget usa "shadow DOM" aberto, o que
   permite estilizar por dentro (EMBED_CSS abaixo).

   Precisa de internet (o avatar é carregado de vlibras.gov.br).
*/
const VLIBRAS_APP_URL = 'https://vlibras.gov.br/app';
const VLIBRAS_LOAD_TIMEOUT_MS = 30000; // o player 3D é pesado; na 1ª vez pode demorar
const VLIBRAS_PLAYER_MARGIN = 8;        // o player do widget tem 8px de margem embaixo

// Com o avatar aberto, o VLibras liga um modo "clique em qualquer texto da página
// pra traduzir": ele escuta TODOS os cliques (antes do nosso app) e os bloqueia
// (preventDefault + stopPropagation) — inclusive o botão de enviar. Ele só deixa
// passar cliques marcados com esta propriedade (é a marca que ele usa nos cliques
// que ele mesmo gera). Conferido no código publicado em vlibras.gov.br.
const VLIBRAS_PASS_FLAG = '__vlibrasSyntheticClick';

// Quando o avatar termina de carregar, o widget AGENDA uma apresentação de
// boas-vindas (~15 sinais) pra 500ms depois. Se a nossa frase sair antes disso,
// a apresentação começa por cima e a "engole". Então esperamos esse tempo
// passar, interrompemos a apresentação e só aí sinalizamos.
const VLIBRAS_WELCOME_DELAY_MS = 1200; // 500ms do widget + folga

// Estilos aplicados DENTRO do widget. As variáveis --sz-* e o tamanho
// (--widget-width / --player-height) são atualizados a cada quadro em _follow().
const EMBED_CSS = `
  #vlibras-app {
    top: var(--sz-top) !important; left: var(--sz-left) !important;
    right: auto !important; bottom: auto !important;
    transform: none !important; translate: none !important; /* o Tailwind v4 desloca com a propriedade translate */
    animation: none !important; transition: opacity .2s !important;
    visibility: var(--sz-vis, visible) !important; /* escondido quando a área do card some (ex.: <details> fechado) */
  }
  #vlibras-app-panel { border-radius: 16px !important; box-shadow: none !important; outline: none !important; }
  /* Cabeçalho (menu, expandir, fechar) e barra de controles: o nosso card já tem
     os dele. Achados pelos ids que existem DENTRO deles — a estrutura em volta
     muda entre versões do widget (conferido na versão publicada e na do GitHub).
     O :not(:has(iframe)) garante que nunca escondemos o bloco do avatar. */
  #vlibras-app-content div:has(#header-actions):not(:has(iframe)),
  #vlibras-app-content div:has(#main-action-speed-options):not(:has(iframe)) { display: none !important; }
`;

const LibrasPlayer = {
  _started: false,
  _stage: null,
  _readyAt: 0,   // quando o avatar ficou pronto (pra saber se a apresentação já foi disparada)
  _styled: false,
  _lastRect: '',

  /** Área do nosso card onde o avatar deve aparecer. */
  embedIn(stageEl) {
    this._stage = stageEl;
  },

  // Marca os cliques feitos dentro do nosso app pra o VLibras deixá-los passar.
  // Registrado no `document` na fase de captura: roda ANTES do escutador dele,
  // que fica no `body`.
  _protectClicks() {
    const scope = this._stage?.closest('.app') || document.body;
    document.addEventListener('click', event => {
      if (scope.contains(event.target)) {
        Object.defineProperty(event, VLIBRAS_PASS_FLAG, { value: true });
      }
    }, true);
  },

  /** O script do VLibras carregou? (sem internet, não carrega) */
  available() {
    return Boolean(window.VLibras && window.VLibras.Widget);
  },

  start() {
    if (this._started || !this.available()) return;
    this._protectClicks();
    new window.VLibras.Widget(VLIBRAS_APP_URL);
    this._started = true;
    if (this._stage) this._follow();
  },

  _host() {
    return document.getElementById('vlibras-app-root');
  },

  // A cada quadro, cola a janela do widget em cima da área do card. Assim ela
  // acompanha qualquer mudança de layout (girar a tela, inverter os cards...).
  _follow() {
    const tick = () => {
      const host = this._host();
      if (host && host.shadowRoot) {
        if (!this._styled) {
          const style = document.createElement('style');
          style.textContent = EMBED_CSS;
          host.shadowRoot.appendChild(style);
          this._styled = true;
        }
        const r = this._stage.getBoundingClientRect();
        const key = [r.left, r.top, r.width, r.height].map(Math.round).join('|');
        if (key !== this._lastRect) {
          this._lastRect = key;
          const visible = r.width > 2 && r.height > 2;
          host.style.setProperty('--sz-vis', visible ? 'visible' : 'hidden');
          host.style.setProperty('--sz-left', visible ? `${r.left}px` : '-9999px'); // e joga pra fora da tela, por garantia
          host.style.setProperty('--sz-top', `${r.top}px`);
          host.style.setProperty('--widget-width', `${r.width}px`);
          host.style.setProperty('--player-height', `${Math.max(0, r.height - VLIBRAS_PLAYER_MARGIN)}px`);
        }
      }
      requestAnimationFrame(tick);
    };
    tick();
  },

  /** O avatar já carregou e está pronto pra sinalizar? */
  ready() {
    const isReady = Boolean(this._translateFn());
    if (isReady && !this._readyAt) this._readyAt = Date.now();
    return isReady;
  },

  // Função de tradução publicada pelo widget quando o player está pronto.
  _translateFn() {
    if (typeof window.vlibras?.translateAndPlay === 'function') return window.vlibras.translateAndPlay;
    if (typeof window.plugin?.translate === 'function') return window.plugin.translate; // versões antigas
    return null;
  },

  _open() {
    if (typeof window.VLibrasWidget?.open === 'function') {
      window.VLibrasWidget.open();
    } else {
      // reserva: clicar no botão de acessibilidade do próprio widget
      (document.getElementById('vlibras-button') || document.querySelector('[vw-access-button]'))?.click();
    }
  },

  /** Faz o avatar sinalizar o texto. */
  async sign(text) {
    if (!this.available()) {
      throw new Error('VLibras indisponível. Verifique a conexão com a internet.');
    }
    this.start();
    this._open(); // se já estiver aberto, não faz nada de mais

    const startedAt = Date.now();
    let translate = this._translateFn();
    while (!translate) {
      if (Date.now() - startedAt > VLIBRAS_LOAD_TIMEOUT_MS) {
        throw new Error('O avatar do VLibras demorou demais para carregar. Verifique a internet.');
      }
      await new Promise(r => setTimeout(r, 300));
      translate = this._translateFn();
    }

    this.ready(); // registra _readyAt, se for a 1ª vez que vemos o avatar pronto
    await this._skipWelcome();
    await translate(text);
  },

  async _skipWelcome() {
    const state = () => window.vlibras || {};
    if (state().isWelcomeFinished) return; // apresentação já acabou (ou foi pulada)

    // Garante que a apresentação já foi disparada antes de tentarmos pará-la
    // (parar antes dela começar não tem efeito — testado na versão publicada).
    const waitMs = VLIBRAS_WELCOME_DELAY_MS - (Date.now() - this._readyAt);
    if (waitMs > 0) await new Promise(r => setTimeout(r, waitMs));

    if (state().isPlayingWelcome && typeof state().stop === 'function') {
      state().stop();
      await new Promise(r => setTimeout(r, 300));
    }
  }
};
