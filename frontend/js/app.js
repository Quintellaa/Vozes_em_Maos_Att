/* Sinaliza — inicialização da página (carregar por último, depois dos demais módulos) */
document.addEventListener('click', e => {
  const toastTrigger = e.target.closest('[data-toast]');
  if (toastTrigger) {
    e.preventDefault();
    toast(toastTrigger.dataset.toast);
    return;
  }
  if (e.target.closest('[data-login]')) instantDemoLogin();
});

const page = document.body.dataset.page;
const currentUser = getCurrentUser();
$$('[data-ini]').forEach(el => el.textContent = initials(currentUser ? currentUser.name : DEFAULT_USER.name));

renderNav(page);
renderIcons();
pages[page]?.();
