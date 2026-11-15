/* Sinaliza — lógica específica de cada tela */
const pages = {
  index() {
    // Já está logado? Vai direto para o app.
    if (getToken()) location.replace('tradutor.html');
  },

  google() {
    // MOCK: login social sem OAuth real — troque por Google Identity Services antes de produção.
    $('#go').onclick = async () => {
      try {
        await loginSocial('google', 'Gabriel Silva', 'gabriel.silva@gmail.com');
      } catch (err) {
        toast(err.message);
      }
    };
  },

  apple() {
    // MOCK: login social sem OAuth real — troque por Sign in with Apple JS antes de produção.
    $('#go').onclick = async () => {
      const hideEmail = $('#hide').checked;
      try {
        await loginSocial(
          'apple',
          'Gabriel Silva',
          hideEmail ? 'gabriel.silva@privaterelay.appleid.com' : 'gabriel.silva@icloud.com'
        );
      } catch (err) {
        toast(err.message);
      }
    };
  },

  login() {
    if (getToken()) return location.replace('tradutor.html');

    const EMAIL_OK = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    const formEntrar = $('#fEntrar');
    const formCriar = $('#fCriar');
    const formEsqueci = $('#fEsqueci');

    // ---- Abas Entrar / Criar conta, e a tela "Esqueci a senha" ----
    // (login.html#criar abre direto no cadastro; login.html#esqueci, na recuperação de senha)
    const TITULOS = { entrar: 'Entrar', criar: 'Criar conta', esqueci: 'Esqueci a senha' };
    const PRIMEIRO_CAMPO = { entrar: '#em', criar: '#cNome', esqueci: '#eEm' };
    function mostrar(modo, focar = true) {
      formEntrar.hidden = modo !== 'entrar';
      formCriar.hidden = modo !== 'criar';
      formEsqueci.hidden = modo !== 'esqueci';
      $('.lg-abas').hidden = modo === 'esqueci';
      $('#abaEntrar').setAttribute('aria-selected', String(modo === 'entrar'));
      $('#abaCriar').setAttribute('aria-selected', String(modo === 'criar'));
      document.title = 'Vozes em Mãos — ' + TITULOS[modo];
      history.replaceState(null, '', '#' + modo);
      $('#errEntrar').textContent = $('#errCriar').textContent = $('#errEsqueci').textContent = '';
      if (focar) setTimeout(() => $(PRIMEIRO_CAMPO[modo]).focus(), 0);
    }
    $('#abaEntrar').onclick = () => mostrar('entrar');
    $('#abaCriar').onclick = () => mostrar('criar');
    document.addEventListener('click', e => {
      const link = e.target.closest('[data-ir]');
      if (!link) return;
      e.preventDefault();
      // leva o e-mail digitado de um formulário para o outro
      const emailDigitado = [$('#em'), $('#cEm'), $('#eEm')].find(inp => !inp.closest('form').hidden && inp.value)?.value;
      const destino = link.dataset.ir;
      if (emailDigitado) $({ entrar: '#em', criar: '#cEm', esqueci: '#eEm' }[destino]).value = emailDigitado;
      mostrar(destino);
    });
    mostrar(TITULOS[location.hash.slice(1)] ? location.hash.slice(1) : 'entrar', false);
    // apaga a mensagem de erro assim que a pessoa volta a digitar
    formEntrar.addEventListener('input', () => { $('#errEntrar').textContent = ''; });
    formCriar.addEventListener('input', () => { $('#errCriar').textContent = ''; });
    formEsqueci.addEventListener('input', () => { $('#errEsqueci').textContent = ''; $('#okEsqueci').hidden = true; });

    // ---- Mostrar/ocultar senha ----
    $$('[data-olho]').forEach(btn => {
      btn.onclick = () => {
        const inp = $('#' + btn.dataset.olho);
        const ver = inp.type === 'password';
        inp.type = ver ? 'text' : 'password';
        btn.setAttribute('aria-pressed', String(ver));
        btn.setAttribute('aria-label', ver ? 'Ocultar senha' : 'Mostrar senha');
      };
    });

    async function enviando(btn, texto, acao) {
      const original = btn.textContent;
      btn.disabled = true;
      btn.textContent = texto;
      try { await acao(); } finally { btn.disabled = false; btn.textContent = original; }
    }

    // ---- Esqueci a senha: envia o link por e-mail ----
    formEsqueci.onsubmit = async e => {
      e.preventDefault();
      const err = $('#errEsqueci');
      const ok = $('#okEsqueci');
      const email = $('#eEm').value.trim();
      err.textContent = '';
      ok.hidden = true;
      if (!EMAIL_OK.test(email)) { err.textContent = 'Digite um e-mail válido, como nome@email.com.'; return $('#eEm').focus(); }

      await enviando($('#btnEsqueci'), 'Enviando…', async () => {
        try {
          await Api.forgotPassword(email);
          ok.textContent = `Pronto! Se ${email} tiver uma conta, você vai receber um e-mail com o link para criar uma nova senha. ` +
            'Confira também a caixa de spam. O link vale por 30 minutos.';
          ok.hidden = false;
          $('#em').value = email;
        } catch (ex) {
          err.textContent = ex.message;
        }
      });
    };

    // ---- Entrar ----
    formEntrar.onsubmit = async e => {
      e.preventDefault();
      const err = $('#errEntrar');
      const email = $('#em').value.trim();
      const senha = $('#pw').value;
      err.textContent = '';
      if (!EMAIL_OK.test(email)) { err.textContent = 'Digite um e-mail válido, como nome@email.com.'; return $('#em').focus(); }
      if (!senha) { err.textContent = 'Digite sua senha.'; return $('#pw').focus(); }

      await enviando($('#btnEntrar'), 'Entrando…', async () => {
        try {
          await loginWithEmail(email, senha);
        } catch (ex) {
          err.textContent = ex.message;
          if (ex.status === 401) {
            // O celular às vezes preenche sozinho a senha de outra conta do mesmo site.
            err.insertAdjacentHTML('beforeend', ' Toque no olho para conferir a senha: o celular pode ter preenchido a de outra conta. Ainda não tem conta? <a href="#criar" data-ir="criar">Crie agora</a>.');
            $('#pw').select();
          }
        }
      });
    };

    // ---- Criar conta ----
    function forcaSenha(s) {
      if (!s) return 0;
      let pontos = 0;
      if (s.length >= 6) pontos++;
      if (s.length >= 10) pontos++;
      if (/[a-z]/i.test(s) && /\d/.test(s)) pontos++;
      if (/[^a-z0-9]/i.test(s)) pontos++;
      return s.length < 6 ? 1 : Math.min(3, Math.max(1, pontos));
    }
    $('#cPw').oninput = () => {
      const v = $('#cPw').value;
      const nivel = forcaSenha(v);
      $('#forca').dataset.nivel = nivel;
      $('#forca small').textContent = !v ? '' : v.length < 6 ? 'Muito curta' : ['', 'Fraca', 'Média', 'Forte'][nivel];
    };

    formCriar.onsubmit = async e => {
      e.preventDefault();
      const err = $('#errCriar');
      const nome = $('#cNome').value.replace(/\s+/g, ' ').trim();
      const email = $('#cEm').value.trim();
      const senha = $('#cPw').value;
      const conf = $('#cPw2').value;
      err.textContent = '';
      if (nome.length < 2) { err.textContent = 'Digite seu nome (mínimo 2 letras).'; return $('#cNome').focus(); }
      if (!EMAIL_OK.test(email)) { err.textContent = 'Digite um e-mail válido, como nome@email.com.'; return $('#cEm').focus(); }
      if (senha.length < 6) { err.textContent = 'A senha precisa ter ao menos 6 caracteres.'; return $('#cPw').focus(); }
      if (senha !== conf) { err.textContent = 'As senhas não são iguais.'; return $('#cPw2').focus(); }

      await enviando($('#btnCriar'), 'Criando conta…', async () => {
        try {
          await registerAccount(nome, email, senha);
        } catch (ex) {
          err.textContent = ex.message;
          if (ex.status === 409) {
            err.textContent = 'Este e-mail já tem uma conta. ';
            err.insertAdjacentHTML('beforeend', '<a href="#entrar" data-ir="entrar">Entrar com ele</a>.');
          }
        }
      });
    };
  },

  // Página aberta pelo link do e-mail: redefinir-senha.html#token=...
  redefinir() {
    // Código do link do e-mail: #c=... (links antigos usavam #token=...)
    const params = new URLSearchParams(location.hash.slice(1));
    const token = params.get('c') || params.get('token');
    // Tira o token da barra de endereço (e do histórico do navegador) assim que lê.
    history.replaceState(null, '', location.pathname);

    const form = $('#fRedefinir');
    const err = $('#errRedefinir');
    if (!token) {
      form.hidden = true;
      $('#semToken').hidden = false;
      return;
    }

    $$('[data-olho]').forEach(btn => {
      btn.onclick = () => {
        const inp = $('#' + btn.dataset.olho);
        const ver = inp.type === 'password';
        inp.type = ver ? 'text' : 'password';
        btn.setAttribute('aria-pressed', String(ver));
        btn.setAttribute('aria-label', ver ? 'Ocultar senha' : 'Mostrar senha');
      };
    });
    form.addEventListener('input', () => { err.textContent = ''; });

    form.onsubmit = async e => {
      e.preventDefault();
      const senha = $('#rPw').value;
      const conf = $('#rPw2').value;
      err.textContent = '';
      if (senha.length < 6) { err.textContent = 'A senha precisa ter ao menos 6 caracteres.'; return $('#rPw').focus(); }
      if (senha !== conf) { err.textContent = 'As senhas não são iguais.'; return $('#rPw2').focus(); }

      const btn = $('#btnRedefinir');
      btn.disabled = true;
      btn.textContent = 'Salvando…';
      try {
        finishLogin(await Api.resetPassword(token, senha)); // já entra no app com a senha nova
      } catch (ex) {
        err.textContent = ex.message;
        if (ex.status === 400) err.insertAdjacentHTML('beforeend', ' <a href="login.html#esqueci">Pedir novo link</a>.');
        btn.disabled = false;
        btn.textContent = 'Salvar nova senha';
      }
    };
  },

  permissao() {
    const goToTranslator = () => location.href = 'tradutor.html';

    $('#allow').onclick = () => {
      if (!navigator.mediaDevices) return goToTranslator();
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          stream.getTracks().forEach(track => track.stop());
          Storage.set(cameraKey(), 'granted');
          goToTranslator();
        })
        .catch(() => {
          Storage.set(cameraKey(), 'denied');
          goToTranslator();
        });
    };
    $('#deny').onclick = () => { Storage.set(cameraKey(), 'denied'); goToTranslator(); };
    $('#skip').onclick = () => Storage.set(cameraKey(), 'skipped');
  },

  tradutor() {
    const transcriptEl = $('#trans');
    const outputEl = $('#out');
    const inputEl = $('#txt');
    const videoEl = $('#video');
    const handsEl = $('#hands');
    const overlayEl = $('#handOverlay');

    // ---- Frase: os sinais reconhecidos vão se juntando, um depois do outro ----
    const phraseWords = [];
    const phraseBoxEl = $('#phraseBox');
    const phraseEl = $('#phrase');

    function renderPhrase() {
      phraseBoxEl.hidden = phraseWords.length === 0;
      phraseEl.textContent = phraseWords.join(' ');
    }

    $('#speak').onclick = () => {
      if (!Speech.speak(phraseWords.join(' '))) toast('Seu navegador não tem voz disponível.');
    };

    $('#clearPhrase').onclick = () => {
      phraseWords.length = 0;
      renderPhrase();
    };

    // ---- Lista de sinais que o modelo conhece (vem da API, não fica fixa no front) ----
    Api.recognitionInfo()
      .then(info => {
        $('#knownList').textContent = info.available
          ? info.classes.map(g => info.words?.[g] || glossToWord(g)).join(', ')
          : 'Reconhecimento indisponível no servidor no momento.';
      })
      .catch(() => { $('#knownList').textContent = 'Não foi possível carregar a lista.'; });

    if (Storage.get(cameraKey()) === 'granted') {
      videoEl.hidden = false;
      handsEl.hidden = true;
      transcriptEl.textContent = 'Sinalize uma palavra e faça uma pausa.';
      Recognizer.start(videoEl, {
        overlayEl,
        onPhrase(gloss, confidence, alternatives, word) {
          transcriptEl.textContent = `"${word}" (${Math.round(confidence * 100)}%)`;
          phraseWords.push(word);
          renderPhrase();
          // a pessoa ouvinte escuta na hora, sem olhar a tela (pode desligar em Perfil > Acessibilidade)
          if (Prefs.get('falarSinais')) Speech.speak(word);
          Prefs.avisarSinal(); // som/vibração, conforme Perfil > Notificações
          addHistoryEntry('l', word).catch(reportApiError);
        },
        onStatus(message) {
          transcriptEl.textContent = message;
        },
        onError(message) {
          transcriptEl.textContent = message;
        }
      });
    }

    // Texto → Libras: quem sinaliza é o avatar do VLibras (ver js/vlibras.js).
    const playBtn = $('#play');
    let lastText = '';

    LibrasPlayer.embedIn($('#librasStage')); // o avatar aparece dentro do nosso card
    LibrasPlayer.start(); // prepara o VLibras, sem abrir o avatar ainda

    async function signText(text) {
      lastText = text;
      if (!LibrasPlayer.ready()) toast('Carregando o avatar do VLibras (a 1ª vez demora)...');
      $('#librasHint').hidden = true;
      playBtn.hidden = false;
      try {
        outputEl.textContent = text;
        await LibrasPlayer.sign(text);
        return true;
      } catch (err) {
        toast(err.message);
        return false;
      }
    }

    playBtn.onclick = () => { if (lastText) signText(lastText); };

    $('#form').onsubmit = async e => {
      e.preventDefault();
      const text = inputEl.value.trim();
      if (!text) return;
      inputEl.value = '';
      if (await signText(text)) {
        addHistoryEntry('t', text).catch(reportApiError);
      }
    };

    $('#swap').onclick = () => $('#cards').classList.toggle('flip');

    $('#mic').onclick = () => {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognitionAPI) return toast('Seu navegador não suporta voz');

      const recognition = new SpeechRecognitionAPI();
      recognition.lang = 'pt-BR';
      $('#mic').classList.add('on');
      recognition.onresult = e => { inputEl.value = e.results[0][0].transcript; };
      recognition.onend = () => {
        $('#mic').classList.remove('on');
        if (inputEl.value) $('#form').requestSubmit();
      };
      recognition.onerror = () => toast('Não consegui ouvir. Tente de novo.');
      recognition.start();
    };
  },

  historico() {
    let activeFilter = 'all';
    const listEl = $('#list');
    const searchEl = $('#q');

    const formatDate = isoString => {
      const date = new Date(isoString);
      const today = new Date();
      const yesterday = new Date(today.getTime() - 864e5);
      const isSameDay = (a, b) => a.toDateString() === b.toDateString();
      const label = isSameDay(date, today) ? 'HOJE' : isSameDay(date, yesterday) ? 'ONTEM' : date.toLocaleDateString('pt-BR');
      const time = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      return [label, time];
    };

    async function render() {
      let items;
      try {
        items = await getHistory({
          type: activeFilter === 'all' || activeFilter === 'fav' ? undefined : activeFilter,
          favorite: activeFilter === 'fav' ? true : undefined,
          search: searchEl.value.trim() || undefined
        });
      } catch (err) {
        reportApiError(err);
        return;
      }

      let lastDayLabel = '';
      listEl.innerHTML = items.map(item => {
        const [dayLabel, time] = formatDate(item.created_at);
        const dayHeader = dayLabel !== lastDayLabel ? `<div class="day">${dayLabel}</div>` : '';
        lastDayLabel = dayLabel;
        const kindLabel = item.type === 'l' ? 'LIBRAS PARA TEXTO' : 'TEXTO PARA LIBRAS';
        const rightLabel = dayLabel === 'HOJE' ? time : dayLabel === 'ONTEM' ? 'Ontem' : dayLabel;
        // item.text pode ter sido digitado pelo usuário: sempre escapar antes de injetar no HTML.
        return `${dayHeader}<div class="item">
          <div class="ic-b"><i data-i="${item.type === 'l' ? 'camera' : 'translate'}"></i></div>
          <div style="flex:1">
            <small>${kindLabel}<em>${rightLabel}</em></small>
            <p>"${escapeHtml(item.text)}"</p>
          </div>
          <button class="star${item.favorite ? ' on' : ''}" data-id="${item.id}" aria-label="Favoritar"><i data-i="star"></i></button>
        </div>`;
      }).join('') || '<p class="empty">Nada por aqui. Toque em + para fazer uma tradução.</p>';

      renderIcons(listEl);
    }

    $('#pills').onclick = e => {
      const btn = e.target.closest('.pill');
      if (!btn) return;
      activeFilter = btn.dataset.f;
      $$('.pill').forEach(p => p.classList.toggle('on', p === btn));
      render();
    };

    listEl.onclick = e => {
      const btn = e.target.closest('.star');
      if (!btn) return;
      toggleHistoryFavorite(btn.dataset.id).then(render).catch(reportApiError);
    };

    searchEl.oninput = debounce(render, 300);

    $('#trash').onclick = () => {
      if (confirm('Apagar todo o histórico?')) {
        clearHistory().then(render).catch(reportApiError);
      }
    };

    render();
  },

  comunidade() {
    // Lista, busca, criação e mural de cada comunidade ficam em js/comunidade.js.
    ComunidadePage.init();
  },

  perfil() {
    // Toda a tela de perfil (dados, foto, comunidades, configurações) fica em js/perfil.js.
    Perfil.init();
  }
};
