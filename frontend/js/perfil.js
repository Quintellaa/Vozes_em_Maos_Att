/* Sinaliza — tela de Perfil
   - Nome e @usuário: salvos no servidor (PATCH /auth/me)
   - Foto e bio: salvas neste aparelho, separadas por conta
   - Comunidades: js/comunidades.js
   - Dados da Conta / Notificações / Acessibilidade: painéis que abrem de baixo
   Chamado por pages.perfil() → Perfil.init()
*/
const Perfil = {
  init() {
    const PROVIDERS = { local: 'E-mail e senha', google: 'Google', apple: 'Apple' };

    let user = getCurrentUser() || { ...DEFAULT_USER, handle: 'usuario' };
    const chaveLocal = () => 'perfilLocal:' + (user.id ?? 'anon');
    const lerLocal = () => Storage.get(chaveLocal(), {}) || {};
    const gravarLocal = dados => Storage.set(chaveLocal(), { ...lerLocal(), ...dados });


    /* ---------- Avatar ---------- */
    function pintarAvatar(img, ini, foto, nome) {
      if (foto) {
        img.src = foto; img.hidden = false; ini.hidden = true;
      } else {
        img.removeAttribute('src'); img.hidden = true; ini.hidden = false;
        ini.textContent = initials(nome || '?') || '?';
      }
    }

    // Foto: a do servidor (aparece para todos); a local só enquanto a antiga não foi enviada.
    const fotoAtual = () => avatarSrc(user) || lerLocal().foto || '';

    // Envia (dataUrl) ou remove ('') a foto no servidor e atualiza a tela toda.
    async function salvarFoto(dataUrl) {
      user = dataUrl ? await Api.setAvatar(dataUrl) : await Api.deleteAvatar();
      Storage.set(USER_KEY, user);
      const { foto, ...resto } = lerLocal(); // a foto não fica mais só no navegador
      Storage.set(chaveLocal(), resto);
      render();
      renderUserAvatar();
    }

    function render() {
      const local = lerLocal();
      $('#nm').textContent = user.name;
      $('#hd').textContent = `Tradutor Iniciante • @${user.handle}`;
      $('#bio').textContent = local.bio || '';
      $('#bio').hidden = !local.bio;
      const foto = fotoAtual();
      pintarAvatar($('#avaImg'), $('#avaIni'), foto, user.name);
      $('#avaBtn').setAttribute('aria-label', foto ? `Foto de ${user.name}. Toque para trocar` : 'Adicionar foto de perfil');

      $('#contaNome').textContent = user.name;
      $('#contaUser').textContent = '@' + user.handle;
      $('#contaEmail').textContent = user.email || '—';
      const provider = user.provider || 'local';
      $('#contaProvider').textContent = PROVIDERS[provider] || provider;
      const social = provider !== 'local';
      $('#formSenha').hidden = social;
      $('#senhaSocial').hidden = !social;
      $('#senhaSocial').textContent = social
        ? `Você entra com ${PROVIDERS[provider] || provider}, então sua senha é gerenciada por lá — não existe senha do Vozes em Mãos para alterar.`
        : '';
    }

    /* ---------- Foto: recorta quadrado e comprime para 256px ---------- */
    function processarFoto(file) {
      return new Promise((ok, erro) => {
        if (!file || !/^image\//.test(file.type)) return erro(new Error('Escolha um arquivo de imagem.'));
        if (file.size > 15 * 1024 * 1024) return erro(new Error('Imagem muito grande (máx. 15 MB).'));
        const url = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
          const lado = Math.min(img.naturalWidth, img.naturalHeight);
          const c = document.createElement('canvas');
          c.width = c.height = 256;
          const ctx = c.getContext('2d');
          ctx.fillStyle = '#fff';
          ctx.fillRect(0, 0, 256, 256);
          ctx.imageSmoothingQuality = 'high';
          ctx.drawImage(img, (img.naturalWidth - lado) / 2, (img.naturalHeight - lado) / 2, lado, lado, 0, 0, 256, 256);
          URL.revokeObjectURL(url);
          ok(c.toDataURL('image/jpeg', 0.85));
        };
        img.onerror = () => { URL.revokeObjectURL(url); erro(new Error('Não consegui abrir essa imagem.')); };
        img.src = url;
      });
    }

    let rascunhoFoto = null; // foto escolhida dentro de "Editar perfil", ainda não salva
    const fotoInput = $('#fotoInput');
    const escolherFoto = () => fotoInput.click();
    $('#avaBtn').onclick = escolherFoto;
    $('#camBtn').onclick = escolherFoto;
    $('#btnEscolherFoto').onclick = escolherFoto;

    fotoInput.onchange = async () => {
      const file = fotoInput.files?.[0];
      fotoInput.value = '';
      if (!file) return;
      try {
        const dataUrl = await processarFoto(file);
        if (!$('#sheetEditar').hidden) {
          rascunhoFoto = dataUrl;
          pintarAvatar($('#prevImg'), $('#prevIni'), dataUrl, $('#inNome').value);
          $('#btnRemoverFoto').hidden = false;
        } else {
          toast('Enviando foto…');
          await salvarFoto(dataUrl);
          toast('Foto atualizada');
        }
      } catch (err) {
        if (err.status === 401) reportApiError(err);
        else toast(err.message || 'Não foi possível salvar a foto.');
      }
    };

    /* ---------- Painéis (abrem de baixo) ---------- */
    let ultimoFoco = null;
    function abrir(id) {
      const sheet = $('#' + id);
      ultimoFoco = document.activeElement;
      sheet.hidden = false;
      document.body.classList.add('pf-travado');
      requestAnimationFrame(() => requestAnimationFrame(() => sheet.classList.add('pf-aberto')));
      setTimeout(() => sheet.querySelector('h3')?.focus?.(), 50);
    }
    function fechar(sheet) {
      if (sheet.hidden) return;
      sheet.classList.remove('pf-aberto');
      setTimeout(() => {
        sheet.hidden = true;
        if (!$$('.pf-sheet').some(s => !s.hidden)) document.body.classList.remove('pf-travado');
      }, 220);
      ultimoFoco?.focus?.();
    }
    $$('.pf-sheet h3').forEach(h => h.setAttribute('tabindex', '-1'));
    $$('.pf-sheet').forEach(s => s.addEventListener('click', e => { if (e.target.closest('[data-fechar]')) fechar(s); }));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') $$('.pf-sheet').forEach(fechar); });
    $$('[data-abrir]').forEach(b => b.addEventListener('click', () => {
      if (b.dataset.abrir === 'sheetNotif') atualizarStatusNotif();
      sincronizarPrefs();
      abrir(b.dataset.abrir);
    }));

    /* ---------- Editar perfil ---------- */
    const contarBio = () => { $('#bioCount').textContent = `${$('#inBio').value.length}/120`; };

    function abrirEdicao() {
      const local = lerLocal();
      rascunhoFoto = null;
      $('#inNome').value = user.name;
      $('#inUser').value = user.handle;
      $('#inBio').value = local.bio || '';
      $('#errNome').textContent = $('#errUser').textContent = '';
      contarBio();
      pintarAvatar($('#prevImg'), $('#prevIni'), fotoAtual(), user.name);
      $('#btnRemoverFoto').hidden = !fotoAtual();
      abrir('sheetEditar');
    }
    $('#btnEditar').onclick = abrirEdicao;
    $('#contaEditar').onclick = () => { fechar($('#sheetConta')); setTimeout(abrirEdicao, 230); };

    $('#inBio').oninput = contarBio;
    $('#inNome').oninput = () => {
      if ($('#prevImg').hidden) $('#prevIni').textContent = initials($('#inNome').value || '?') || '?';
    };
    // @usuário: só minúsculas, números, ponto e _ (tira acentos e espaços enquanto digita)
    $('#inUser').oninput = function () {
      const limpo = this.value.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9._]/g, '');
      if (limpo !== this.value) this.value = limpo;
    };
    $('#btnRemoverFoto').onclick = function () {
      rascunhoFoto = '';
      pintarAvatar($('#prevImg'), $('#prevIni'), '', $('#inNome').value);
      this.hidden = true;
    };

    $('#formEditar').onsubmit = async e => {
      e.preventDefault();
      const nome = $('#inNome').value.replace(/\s+/g, ' ').trim();
      const handle = $('#inUser').value.trim();
      $('#errNome').textContent = $('#errUser').textContent = '';

      let ok = true;
      if (nome.length < 2) { $('#errNome').textContent = 'Digite seu nome (mínimo 2 letras).'; ok = false; }
      // só valida o @ se ele mudou (contas antigas podem ter um @ curto vindo do e-mail)
      if (handle !== user.handle && !/^[a-z0-9._]{3,20}$/.test(handle)) { $('#errUser').textContent = 'Use de 3 a 20 caracteres: letras, números, ponto ou _.'; ok = false; }
      if (!ok) return;

      const mudou = {};
      if (nome !== user.name) mudou.name = nome;
      if (handle !== user.handle) mudou.handle = handle;

      const btn = $('#btnSalvarPerfil');
      btn.disabled = true;
      btn.textContent = 'Salvando…';
      try {
        if (Object.keys(mudou).length) {
          user = await Api.updateMe(mudou);
          Storage.set(USER_KEY, user);
        }
        gravarLocal({ bio: $('#inBio').value.trim() });
        if (rascunhoFoto !== null) await salvarFoto(rascunhoFoto); // '' = remover
        render();
        fechar($('#sheetEditar'));
        toast('Perfil atualizado');
      } catch (err) {
        if (err.status === 409) $('#errUser').textContent = err.message;
        else if (err.status === 401) reportApiError(err);
        else toast(err.message || 'Não foi possível salvar.');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Salvar';
      }
    };

    /* ---------- Dados da Conta: alterar senha ---------- */
    $('#mostrarSenhas').onchange = e => {
      ['#inSenhaAtual', '#inSenhaNova', '#inSenhaConf'].forEach(s => { $(s).type = e.target.checked ? 'text' : 'password'; });
    };
    $('#formSenha').onsubmit = async e => {
      e.preventDefault();
      const atual = $('#inSenhaAtual').value;
      const nova = $('#inSenhaNova').value;
      const conf = $('#inSenhaConf').value;
      const err = $('#errSenha');
      err.textContent = '';
      if (!atual) return (err.textContent = 'Digite sua senha atual.');
      if (nova.length < 6) return (err.textContent = 'A nova senha precisa ter ao menos 6 caracteres.');
      if (nova !== conf) return (err.textContent = 'A confirmação não é igual à nova senha.');
      if (nova === atual) return (err.textContent = 'A nova senha precisa ser diferente da atual.');

      const btn = $('#btnSenha');
      btn.disabled = true;
      btn.textContent = 'Alterando…';
      try {
        await Api.changePassword(atual, nova);
        $('#formSenha').reset();
        toast('Senha alterada');
      } catch (e2) {
        if (e2.status === 401) reportApiError(e2);
        else err.textContent = e2.message;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Alterar senha';
      }
    };

    $('#limparAparelho').onclick = () => {
      if (!confirm('Apagar a bio e as preferências salvas neste aparelho? Seu nome, usuário, foto, comunidades e histórico continuam na conta.')) return;
      Storage.remove(chaveLocal());
      Storage.remove(PREFS_KEY);
      Storage.remove('lembreteUltimo');
      Prefs.aplicar();
      Prefs.agendarLembrete();
      sincronizarPrefs();
      render();
      toast('Dados deste aparelho apagados');
    };
    $('#contaSair').onclick = logout;
    $('#exit').onclick = logout;

    /* ---------- Preferências (Notificações e Acessibilidade) ---------- */
    function sincronizarPrefs() {
      const p = Prefs.todas();
      $$('[data-pref]').forEach(inp => { inp.checked = !!p[inp.dataset.pref]; });
      $$('[data-pref-seg]').forEach(grupo => {
        const atual = String(p[grupo.dataset.prefSeg]);
        $$('button', grupo).forEach(b => b.setAttribute('aria-checked', String(b.dataset.v === atual)));
      });
      $('#inLembreteHora').value = p.lembreteHora;
      $('#inLembreteHora').disabled = !p.lembrete;
    }

    $$('[data-pref]').forEach(inp => inp.addEventListener('change', async () => {
      const chave = inp.dataset.pref;
      if (chave === 'lembrete' && inp.checked && Prefs.statusNotificacao() !== 'granted') {
        const r = await Prefs.pedirPermissaoNotificacao();
        atualizarStatusNotif();
        if (r !== 'granted') {
          inp.checked = false;
          toast(r === 'unsupported' ? 'Este navegador não suporta notificações.' : 'Permita as notificações para receber o lembrete.');
          return;
        }
      }
      Prefs.set(chave, inp.checked);
      sincronizarPrefs();
      if (chave === 'somSinal' && inp.checked) Prefs.bip();
      if (chave === 'vibrarSinal' && inp.checked) Prefs.vibrar();
    }));

    $$('[data-pref-seg]').forEach(grupo => grupo.addEventListener('click', e => {
      const b = e.target.closest('button[data-v]');
      if (!b) return;
      const chave = grupo.dataset.prefSeg;
      const valor = chave === 'velocidadeVoz' ? Number(b.dataset.v) : b.dataset.v;
      Prefs.set(chave, valor);
      sincronizarPrefs();
    }));

    $('#inLembreteHora').onchange = e => {
      if (e.target.value) { Prefs.set('lembreteHora', e.target.value); toast(`Lembrete às ${e.target.value}`); }
    };

    $('#testarAviso').onclick = () => {
      Prefs.bip();
      Prefs.vibrar();
    };

    $('#ouvirVoz').onclick = () => {
      if (!Speech.speak('Olá! Esta é a voz do Vozes em Mãos.')) toast('Seu navegador não tem voz disponível.');
    };

    function atualizarStatusNotif() {
      const st = Prefs.statusNotificacao();
      const btn = $('#notifPermitir');
      const box = $('#notifStatus');
      const TXT = {
        granted: ['Notificações permitidas', 'Você vai receber os lembretes neste navegador.', 'Testar'],
        denied: ['Notificações bloqueadas', 'Libere no cadeado ao lado do endereço do site e recarregue a página.', ''],
        default: ['Notificações desligadas', 'Permita para receber lembretes de prática.', 'Permitir'],
        unsupported: ['Sem suporte a notificações', 'Este navegador não permite notificações.', '']
      }[st];
      $('#notifStatusTxt').textContent = TXT[0];
      $('#notifStatusSub').textContent = TXT[1];
      btn.textContent = TXT[2];
      btn.hidden = !TXT[2];
      box.dataset.status = st;
    }
    $('#notifPermitir').onclick = async () => {
      if (Prefs.statusNotificacao() === 'granted') {
        if (!Prefs.notificar('Vozes em Mãos', 'As notificações estão funcionando ✋')) toast('Não foi possível mostrar a notificação.');
        return;
      }
      await Prefs.pedirPermissaoNotificacao();
      atualizarStatusNotif();
      Prefs.agendarLembrete();
    };

    /* ---------- Comunidades (do servidor, via js/comunidades.js) ---------- */
    function renderComunidades() {
      const lista = Comunidades.listar();
      const box = $('#comLista');
      $('#verTodas').hidden = lista.length === 0;
      $('#verTodas').textContent = lista.length > 2 ? `Ver todas (${lista.length})` : 'Ver todas';
      const icone = c => `<span class="pf-com-ic pf-cor-${Comunidades.cor(c.color)}">${Comunidades.svg(c.icon)}</span>`;

      if (!lista.length) {
        box.className = 'pf-com pf-com-vazio';
        box.innerHTML = `<span class="pf-com-ic pf-cor-blue">${Comunidades.svg('users')}</span>
          <div><strong>Você ainda não entrou em nenhuma comunidade</strong>
          <small>Encontre grupos para praticar Libras com outras pessoas.</small></div>
          <a class="pf-btn" href="comunidade.html">Explorar</a>`;
        return;
      }
      box.className = 'pf-com';
      box.innerHTML = lista.slice(0, 2).map(c => `
        <a class="pf-com-card" href="comunidade.html?id=${c.id}">
          ${icone(c)}
          <strong>${escapeHtml(c.name)}</strong><small>${Comunidades.formatarMembros(c.member_count)}</small>
        </a>`).join('');

      $('#comTodas').innerHTML = lista.map(c => `
        <li><a class="pf-com-link" href="comunidade.html?id=${c.id}">${icone(c)}
          <span class="pf-com-info"><strong>${escapeHtml(c.name)}</strong><small>${Comunidades.formatarMembros(c.member_count)}</small></span></a>
          <button type="button" class="pf-sair" data-sair="${c.id}" data-nome="${escapeHtml(c.name)}">Sair</button></li>`).join('');
    }
    $('#verTodas').onclick = () => abrir('sheetCom');
    $('#comTodas').onclick = async e => {
      const b = e.target.closest('[data-sair]');
      if (!b || !confirm(`Sair da comunidade "${b.dataset.nome}"?`)) return;
      b.disabled = true;
      try {
        await Comunidades.sair(Number(b.dataset.sair));
        toast(`Você saiu de ${b.dataset.nome}`);
        if (!Comunidades.listar().length) fechar($('#sheetCom'));
      } catch (err) {
        b.disabled = false;
        reportApiError(err);
      }
    };
    window.addEventListener('comunidades:mudou', renderComunidades);

    /* ---------- Início ---------- */
    render();
    renderComunidades();
    Comunidades.sincronizar().catch(reportApiError); // traz do servidor as comunidades em que você entrou
    // Números do cartão (conta nova começa tudo em 0)
    Api.myStats()
      .then(st => {
        const fmt = n => (Number(n) || 0).toLocaleString('pt-BR');
        $('#stTrad').textContent = fmt(st.translations);
        $('#stAulas').textContent = fmt(st.lessons);
        $('#stSelos').textContent = fmt(st.badges);
      })
      .catch(reportApiError);
    sincronizarPrefs();
    atualizarStatusNotif();
    // Atualiza com os dados mais recentes do servidor, sem travar a tela.
    refreshCurrentUser()
      .then(syncLocalPhoto)
      .then(fresh => { user = fresh; render(); renderUserAvatar(); })
      .catch(reportApiError);
  }
};
