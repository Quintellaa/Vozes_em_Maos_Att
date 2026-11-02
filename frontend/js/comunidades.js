/* Sinaliza — comunidades do usuário (dados no servidor, via api.js)
   Guarda uma cópia local das comunidades em que o usuário entrou, para o
   Perfil aparecer na hora, e atualiza com o servidor em segundo plano.

     Comunidades.listar()        → cópia local (array), sem esperar a rede
     await Comunidades.sincronizar()
     await Comunidades.entrar(id) / await Comunidades.sair(id)
     Comunidades.formatarMembros(2400) → "2,4 mil membros"

   Sempre que a lista muda dispara o evento 'comunidades:mudou' na window.
*/
const COMUNIDADE_ICONES = {
  cap: '<path d="M2 9l10-5 10 5-10 5zM6 11v5c3 2 9 2 12 0v-5"/>',
  building: '<path d="M5 21V4h14v17M9 8h2M13 8h2M9 12h2M13 12h2M10 21v-4h4v4"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6M16 4.5a3.5 3.5 0 0 1 0 7M18 14c2.5.6 4 2.6 4 6"/>',
  heart: '<path d="M12 20s-7.5-4.4-7.5-10A4.2 4.2 0 0 1 12 7.4 4.2 4.2 0 0 1 19.5 10c0 5.6-7.5 10-7.5 10z"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19V5"/>',
  hand: '<path d="M8 12V5.5a1.5 1.5 0 0 1 3 0V11M11 10V4.5a1.5 1.5 0 0 1 3 0V11M14 10.5V6a1.5 1.5 0 0 1 3 0v8a6 6 0 0 1-6 6h-.5a6 6 0 0 1-4.6-2.2L3.6 15a1.5 1.5 0 0 1 2.3-2L8 15"/>'
};
const COMUNIDADE_CORES = ['blue', 'amber', 'green', 'pink', 'purple'];
const COMUNIDADE_CATEGORIAS = {
  estudos: 'Estudos', saude: 'Saúde', trabalho: 'Trabalho', cultura: 'Cultura', familia: 'Família', geral: 'Geral'
};

const Comunidades = (() => {
  const chave = () => 'comunidades:' + (getCurrentUser()?.id ?? 'anon');
  const avisar = lista => window.dispatchEvent(new CustomEvent('comunidades:mudou', { detail: lista }));
  const ler = () => {
    const lista = Storage.get(chave(), []);
    // descarta o formato antigo (salvo só no navegador, antes de existir no servidor)
    return Array.isArray(lista) ? lista.filter(c => typeof c.id === 'number') : [];
  };
  const gravar = lista => { Storage.set(chave(), lista); avisar(lista); return lista; };

  // Atualiza a cópia local com a versão que veio do servidor para uma comunidade.
  function aplicar(com) {
    const resto = ler().filter(c => c.id !== com.id);
    return gravar(com.joined ? [com, ...resto] : resto);
  }

  window.addEventListener('storage', e => {
    if (e.key === STORAGE_PREFIX + chave()) avisar(ler());
  });

  return {
    listar: ler,
    participa: id => ler().some(c => c.id === Number(id)),
    async sincronizar() {
      return gravar(await Api.listCommunities({ joined: true }));
    },
    async entrar(id) { const com = await Api.joinCommunity(id); aplicar(com); return com; },
    async sair(id) { const com = await Api.leaveCommunity(id); aplicar(com); return com; },
    aplicar,
    svg(icone) {
      return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${COMUNIDADE_ICONES[icone] || COMUNIDADE_ICONES.users}</svg>`;
    },
    cor: c => (COMUNIDADE_CORES.includes(c) ? c : 'blue'),
    formatarMembros(n) {
      n = Number(n) || 0;
      if (n >= 1000) return (n / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' mil membros';
      return n + (n === 1 ? ' membro' : ' membros');
    }
  };
})();
