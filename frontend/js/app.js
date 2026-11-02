/* Sinaliza — inicialização da página (carregar por último, depois dos demais módulos) */

// Service worker: é o que deixa instalar o site como app no celular (ver sw.js).
// Só funciona em https ou localhost; no Live Server via IP da rede ele é ignorado.
if ('serviceWorker' in navigator && window.isSecureContext) {
  navigator.serviceWorker.register('sw.js').catch(() => {});
}
document.addEventListener('click', e => {
  const toastTrigger = e.target.closest('[data-toast]');
  if (toastTrigger) {
    e.preventDefault();
    toast(toastTrigger.dataset.toast);
    return;
  }
});

const page = document.body.dataset.page;
const currentUser = getCurrentUser();
renderUserAvatar();

// Mantém o avatar em dia quando o perfil muda:
// - em outra aba (evento 'storage'),
// - ao voltar para a página pelo botão Voltar do navegador (página restaurada do cache),
// - com os dados mais recentes do servidor (o perfil já faz isso sozinho).
window.addEventListener('storage', e => {
  if (e.key && (e.key === STORAGE_PREFIX + USER_KEY || e.key.startsWith(STORAGE_PREFIX + 'perfilLocal:'))) renderUserAvatar();
});
window.addEventListener('pageshow', e => { if (e.persisted) renderUserAvatar(); });
if (getToken() && page !== 'perfil') {
  refreshCurrentUser()
    .then(syncLocalPhoto)
    .then(() => renderUserAvatar())
    .catch(err => { if (err?.status === 401) reportApiError(err); });
}

renderNav(page);
renderIcons();
pages[page]?.();
