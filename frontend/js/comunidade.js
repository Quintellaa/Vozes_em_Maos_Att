/* Sinaliza — tela de Comunidade
   comunidade.html        → explorar/buscar, filtrar por categoria, entrar e criar
   comunidade.html?id=3   → detalhe da comunidade com o mural de publicações
   Chamado por pages.comunidade() → ComunidadePage.init()
*/
const ComunidadePage = {
  init() {
    const id = Number(new URLSearchParams(location.search).get('id'));
    if (id) this.detalhe(id);
    else this.lista();
    this.criacao();
  },

  /* ================= LISTA ================= */
  lista() {
    $('#vLista').hidden = false;
    $('#vDet').hidden = true;
    let filtro = '';
    let busca = '';
    const listaEl = $('#lista');

    function cartao(c) {
      return `<a class="cm-card" href="comunidade.html?id=${c.id}">
        <span class="pf-com-ic pf-cor-${Comunidades.cor(c.color)}">${Comunidades.svg(c.icon)}</span>
        <span class="cm-card-txt">
          <strong>${escapeHtml(c.name)}</strong>
          ${c.description ? `<span class="cm-card-desc">${escapeHtml(c.description)}</span>` : ''}
          <small>${COMUNIDADE_CATEGORIAS[c.category] || 'Geral'} · ${Comunidades.formatarMembros(c.member_count)}</small>
        </span>
        ${c.joined
          ? '<span class="cm-tag-ok"><i data-i="check"></i>Participando</span>'
          : `<button type="button" class="cm-entrar" data-entrar="${c.id}" aria-label="Entrar em ${escapeHtml(c.name)}">Entrar</button>`}
      </a>`;
    }

    let pedido = 0; // ignora respostas antigas quando a pessoa digita rápido
    async function carregar() {
      const meu = ++pedido;
      if (!listaEl.children.length) listaEl.innerHTML = '<p class="cm-carregando">Carregando comunidades…</p>';
      let itens;
      try {
        itens = await Api.listCommunities({
          search: busca || undefined,
          category: filtro && filtro !== 'minhas' ? filtro : undefined,
          joined: filtro === 'minhas' ? true : undefined
        });
      } catch (err) {
        if (meu === pedido) listaEl.innerHTML = `<p class="empty">${escapeHtml(err.message)}</p>`;
        return reportApiError(err);
      }
      if (meu !== pedido) return;

      if (!itens.length) {
        const msg = filtro === 'minhas' && !busca
          ? 'Você ainda não entrou em nenhuma comunidade.'
          : 'Nenhuma comunidade encontrada.';
        listaEl.innerHTML = `<div class="cm-vazio"><p>${msg}</p>
          <button type="button" class="pf-btn" data-criar>Criar uma comunidade</button></div>`;
        return;
      }
      listaEl.innerHTML = itens.map(cartao).join('');
      renderIcons(listaEl);
    }

    $('#pills').onclick = e => {
      const b = e.target.closest('.pill');
      if (!b) return;
      filtro = b.dataset.f;
      $$('.pill').forEach(p => p.classList.toggle('on', p === b));
      carregar();
    };
    $('#q').oninput = debounce(e => { busca = e.target.value.trim(); carregar(); }, 300);

    listaEl.addEventListener('click', async e => {
      if (e.target.closest('[data-criar]')) return ComunidadePage.abrirCriacao();
      const b = e.target.closest('[data-entrar]');
      if (!b) return;
      e.preventDefault(); // o botão fica dentro do link do cartão
      b.disabled = true;
      b.textContent = '…';
      try {
        const com = await Comunidades.entrar(Number(b.dataset.entrar));
        toast(`Você entrou em ${com.name}`);
        carregar();
      } catch (err) {
        b.disabled = false;
        b.textContent = 'Entrar';
        reportApiError(err);
      }
    });

    carregar();
  },

  /* ================= DETALHE ================= */
  detalhe(id) {
    $('#vLista').hidden = true;
    $('#vDet').hidden = false;
    let com = null;
    let posts = [];

    $('#detVoltar').onclick = () => {
      // volta para onde a pessoa estava (perfil ou lista); se abriu direto, vai para a lista
      if (document.referrer.startsWith(location.origin) && history.length > 1) history.back();
      else location.href = 'comunidade.html';
    };

    function renderInfo() {
      document.title = `Sinaliza — ${com.name}`;
      const cor = Comunidades.cor(com.color);
      $('#detHero').className = `cm-hero cm-hero-${cor}`;
      $('#detIc').className = `cm-info-ic pf-com-ic pf-cor-${cor}`;
      $('#detIc').innerHTML = Comunidades.svg(com.icon);
      $('#detNome').textContent = com.name;
      $('#detMeta').textContent = `${COMUNIDADE_CATEGORIAS[com.category] || 'Geral'} · ${Comunidades.formatarMembros(com.member_count)}${com.is_owner ? ' · Você criou' : ''}`;
      $('#detDesc').textContent = com.description || '';
      $('#detDesc').hidden = !com.description;
      const btn = $('#detEntrar');
      btn.textContent = com.joined ? 'Participando ✓' : 'Entrar na comunidade';
      btn.classList.toggle('cm-saindo', com.joined);
      btn.setAttribute('aria-label', com.joined ? 'Você participa. Toque para sair' : 'Entrar na comunidade');
      $('#composer').hidden = !com.joined;
      $('#convite').hidden = com.joined;
    }

    function tempo(iso) {
      const d = new Date(iso);
      const seg = Math.max(0, (Date.now() - d) / 1000);
      if (seg < 60) return 'agora';
      if (seg < 3600) return `há ${Math.floor(seg / 60)} min`;
      if (seg < 86400) return `há ${Math.floor(seg / 3600)} h`;
      if (seg < 172800) return 'ontem';
      return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
    }

    function renderPosts() {
      $('#detQtd').textContent = posts.length ? `${posts.length} ${posts.length === 1 ? 'publicação' : 'publicações'}` : '';
      if (!posts.length) {
        $('#posts').innerHTML = `<p class="cm-sem-posts">${com?.joined ? 'Ninguém publicou ainda. Que tal começar a conversa?' : 'Ainda não há publicações aqui.'}</p>`;
        return;
      }
      $('#posts').innerHTML = posts.map(p => `
        <article class="cm-post">
          ${p.author.avatar_url
            ? `<span class="ava cm-ava"><img class="ava-img" src="${escapeHtml(avatarSrc(p.author))}" alt="" loading="lazy"></span>`
            : `<span class="ava cm-ava">${escapeHtml(initials(p.author.name) || '?')}</span>`}
          <div class="cm-post-corpo">
            <header><b>${escapeHtml(p.author.name)}${p.mine ? ' <em>(você)</em>' : ''}</b>
              <small>@${escapeHtml(p.author.handle)} · <time datetime="${p.created_at}">${tempo(p.created_at)}</time></small></header>
            <p>${escapeHtml(p.text)}</p>
          </div>
          ${p.can_delete ? `<button type="button" class="cm-apagar" data-apagar="${p.id}" aria-label="Apagar publicação"><i data-i="trash"></i></button>` : ''}
        </article>`).join('');
      renderIcons($('#posts'));
    }

    async function carregarPosts() {
      try {
        posts = await Api.listPosts(id);
        renderPosts();
      } catch (err) {
        reportApiError(err);
      }
    }

    async function carregar() {
      try {
        com = await Api.getCommunity(id);
      } catch (err) {
        if (err.status === 404) {
          $('#vDet').innerHTML = `<div class="cm-vazio cm-404"><p>Essa comunidade não existe mais.</p><a class="pf-btn" href="comunidade.html">Ver comunidades</a></div>`;
          return;
        }
        return reportApiError(err);
      }
      renderInfo();
      carregarPosts();
    }

    $('#detEntrar').onclick = async () => {
      if (!com) return;
      if (com.joined && !confirm(`Sair da comunidade "${com.name}"?`)) return;
      const btn = $('#detEntrar');
      btn.disabled = true;
      try {
        com = com.joined ? await Comunidades.sair(id) : await Comunidades.entrar(id);
        toast(com.joined ? `Você entrou em ${com.name}` : `Você saiu de ${com.name}`);
        renderInfo();
        renderPosts();
        if (com.joined) setTimeout(() => $('#inPost').focus(), 50);
      } catch (err) {
        reportApiError(err);
      } finally {
        btn.disabled = false;
      }
    };

    // ---- Escrever publicação ----
    const inPost = $('#inPost');
    inPost.oninput = () => {
      $('#postCount').textContent = `${inPost.value.length}/1000`;
      $('#btnPublicar').disabled = !inPost.value.trim();
      inPost.style.height = 'auto';
      inPost.style.height = Math.min(inPost.scrollHeight, 220) + 'px';
    };
    inPost.onkeydown = e => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) $('#composer').requestSubmit();
    };
    $('#composer').onsubmit = async e => {
      e.preventDefault();
      const texto = inPost.value.trim();
      if (!texto) return;
      const btn = $('#btnPublicar');
      btn.disabled = true;
      btn.textContent = 'Publicando…';
      try {
        const novo = await Api.createPost(id, texto);
        posts = [novo, ...posts];
        renderPosts();
        inPost.value = '';
        inPost.oninput();
      } catch (err) {
        if (err.status === 403) { com.joined = false; renderInfo(); }
        reportApiError(err);
      } finally {
        btn.textContent = 'Publicar';
        btn.disabled = !inPost.value.trim();
      }
    };

    $('#posts').onclick = async e => {
      const b = e.target.closest('[data-apagar]');
      if (!b || !confirm('Apagar esta publicação?')) return;
      try {
        await Api.deletePost(id, Number(b.dataset.apagar));
        posts = posts.filter(p => p.id !== Number(b.dataset.apagar));
        renderPosts();
        toast('Publicação apagada');
      } catch (err) {
        reportApiError(err);
      }
    };

    // Busca publicações novas de tempos em tempos enquanto a tela está aberta.
    setInterval(() => {
      if (document.visibilityState === 'visible' && com && document.activeElement !== inPost) carregarPosts();
    }, 20000);

    carregar();
  },

  /* ================= CRIAR COMUNIDADE ================= */
  abrirCriacao() {},

  criacao() {
    const sheet = $('#sheetNova');
    const ICONES = ['users', 'cap', 'book', 'hand', 'heart', 'building'];
    let icone = 'users';
    let cor = 'blue';

    $('#escIcone').innerHTML = ICONES.map(i =>
      `<button type="button" role="radio" data-icone="${i}" aria-label="${i}">${Comunidades.svg(i)}</button>`).join('');
    $('#escCor').innerHTML = COMUNIDADE_CORES.map(c =>
      `<button type="button" role="radio" data-cor="${c}" class="cm-cor pf-cor-${c}" aria-label="${c}"></button>`).join('');

    function preview() {
      const nome = $('#inNomeCom').value.trim();
      $('#prevNome').textContent = nome || 'Nome da comunidade';
      $('#prevCat').textContent = COMUNIDADE_CATEGORIAS[$('#inCatCom').value];
      $('#prevIc').className = `pf-com-ic pf-cor-${cor}`;
      $('#prevIc').innerHTML = Comunidades.svg(icone);
      $$('[data-icone]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.icone === icone)));
      $$('[data-cor]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.cor === cor)));
      $('#descCount').textContent = `${$('#inDescCom').value.length}/280`;
    }
    $('#escIcone').onclick = e => { const b = e.target.closest('[data-icone]'); if (b) { icone = b.dataset.icone; preview(); } };
    $('#escCor').onclick = e => { const b = e.target.closest('[data-cor]'); if (b) { cor = b.dataset.cor; preview(); } };
    ['#inNomeCom', '#inDescCom', '#inCatCom'].forEach(s => $(s).addEventListener('input', preview));

    function abrir() {
      $('#formNova').reset();
      icone = 'users';
      cor = 'blue';
      $('#errNomeCom').textContent = '';
      preview();
      sheet.hidden = false;
      document.body.classList.add('pf-travado');
      requestAnimationFrame(() => requestAnimationFrame(() => sheet.classList.add('pf-aberto')));
      setTimeout(() => $('#inNomeCom').focus(), 250);
    }
    function fechar() {
      sheet.classList.remove('pf-aberto');
      document.body.classList.remove('pf-travado');
      setTimeout(() => { sheet.hidden = true; }, 220);
    }
    ComunidadePage.abrirCriacao = abrir;
    $('#btnNova').onclick = abrir;
    sheet.addEventListener('click', e => { if (e.target.closest('[data-fechar]')) fechar(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !sheet.hidden) fechar(); });

    $('#formNova').onsubmit = async e => {
      e.preventDefault();
      const nome = $('#inNomeCom').value.replace(/\s+/g, ' ').trim();
      $('#errNomeCom').textContent = '';
      if (nome.length < 3) {
        $('#errNomeCom').textContent = 'O nome precisa ter ao menos 3 letras.';
        return $('#inNomeCom').focus();
      }
      const btn = $('#btnCriar');
      btn.disabled = true;
      btn.textContent = 'Criando…';
      try {
        const com = await Api.createCommunity({
          name: nome,
          description: $('#inDescCom').value.trim(),
          category: $('#inCatCom').value,
          icon: icone,
          color: cor
        });
        Comunidades.aplicar(com); // já aparece no Perfil
        location.href = `comunidade.html?id=${com.id}`;
      } catch (err) {
        if (err.status === 409) $('#errNomeCom').textContent = err.message;
        else reportApiError(err);
        btn.disabled = false;
        btn.textContent = 'Criar';
      }
    };
  }
};
