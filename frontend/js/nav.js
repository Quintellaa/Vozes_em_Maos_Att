/* Sinaliza — barra de navegação inferior (igual em todas as telas) */
const TABS = [
  ['tradutor', 'translate', 'Tradutor'],
  ['historico', 'history', 'Histórico'],
  ['comunidade', 'users', 'Comunidade'],
  ['perfil', 'user', 'Perfil']
];

function renderNav(currentPage) {
  const el = $('#nav');
  if (!el) return;

  const fab = '<a class="fab" href="tradutor.html" aria-label="Nova tradução"><i data-i="plus"></i></a>';

  const tabs = TABS.map(([slug, icon, label]) => {
    if (slug === 'comunidade') {
      return `<a class="tab" href="#" data-toast="Comunidade em breve"><i data-i="${icon}"></i>${label}</a>`;
    }
    const isActive = slug === currentPage ? ' on' : '';
    return `<a class="tab${isActive}" href="${slug}.html"><i data-i="${icon}"></i>${label}</a>`;
  }).join('');

  el.innerHTML = fab + tabs;
}
