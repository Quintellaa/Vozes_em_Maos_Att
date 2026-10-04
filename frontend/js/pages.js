/* Sinaliza — lógica específica de cada tela */
const pages = {
  index() {},

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
    $('#eye').onclick = () => {
      const pw = $('#pw');
      pw.type = pw.type === 'password' ? 'text' : 'password';
    };

    $('#f').onsubmit = async e => {
      e.preventDefault();
      const email = $('#em').value.trim();
      const password = $('#pw').value;

      if (!/^\S+@\S+\.\S+$/.test(email)) {
        $('#err').textContent = 'Digite um e-mail válido, como nome@email.com.';
        return;
      }
      if (password.length < 6) {
        $('#err').textContent = 'A senha precisa ter ao menos 6 caracteres.';
        return;
      }

      $('#err').textContent = '';
      const handle = email.split('@')[0];
      const name = handle[0].toUpperCase() + handle.slice(1);

      try {
        await loginWithEmail(name, email, password);
      } catch (err) {
        $('#err').textContent = err.message;
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
          Storage.set('cam', 'granted');
          goToTranslator();
        })
        .catch(() => {
          Storage.set('cam', 'denied');
          goToTranslator();
        });
    };
    $('#deny').onclick = () => { Storage.set('cam', 'denied'); goToTranslator(); };
    $('#skip').onclick = () => Storage.set('cam', 'skipped');
  },

  tradutor() {
    const transcriptEl = $('#trans');
    const outputEl = $('#out');
    const avatarEl = $('#avatar');
    const inputEl = $('#txt');
    const videoEl = $('#video');
    const handsEl = $('#hands');
    const overlayEl = $('#handOverlay');

    if (Storage.get('cam') === 'granted') {
      videoEl.hidden = false;
      handsEl.hidden = true;
      transcriptEl.textContent = 'Sinalize uma palavra e faça uma pausa.';
      Recognizer.start(videoEl, {
        overlayEl,
        onPhrase(gloss, confidence) {
          transcriptEl.textContent = `"${gloss}" (${Math.round(confidence * 100)}%)`;
          addHistoryEntry('l', gloss).catch(reportApiError);
        },
        onStatus(message) {
          transcriptEl.textContent = message;
        },
        onError(message) {
          transcriptEl.textContent = message;
        }
      });
    }

    // O avatar só sabe os sinais do dataset. Quando não souber, avisamos em vez
    // de animar algo errado — um sinal incorreto engana quem depende de Libras.
    function playText(text) {
      const { known, gloss } = Avatar.play(avatarEl, text);
      if (known) {
        outputEl.textContent = gloss;
        return true;
      }
      const lista = knownSigns();
      outputEl.textContent = lista.length
        ? `Ainda não sei esse sinal. Sei: ${lista.join(', ')}.`
        : 'Nenhum sinal carregado.';
      return false;
    }

    $('#play').onclick = () => playText(inputEl.value.trim() || outputEl.textContent || '');

    $('#form').onsubmit = e => {
      e.preventDefault();
      const text = inputEl.value.trim();
      if (!text) return;
      if (playText(text)) {
        addHistoryEntry('t', text).catch(reportApiError);
        inputEl.value = '';
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

  perfil() {
    const applyUser = user => {
      $('#nm').textContent = user.name;
      $('#hd').textContent = `Tradutor Iniciante • @${user.handle}`;
    };

    applyUser(getCurrentUser());
    // Atualiza com os dados mais recentes do servidor, sem travar a tela enquanto isso.
    refreshCurrentUser().then(applyUser).catch(reportApiError);

    $('#exit').onclick = logout;
  }
};
