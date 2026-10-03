/* Sinaliza — helpers de DOM e feedback visual */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const TOAST_DURATION_MS = 1800;
let toastTimer;

function toast(message) {
  const el = $('#toast');
  if (!el) return;
  el.textContent = message;
  el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('on'), TOAST_DURATION_MS);
}

// Escapa HTML antes de injetar conteúdo do usuário via innerHTML (evita XSS).
// Use sempre que um valor vindo do usuário (texto digitado, reconhecido pela câmera etc.)
// for interpolado em um template de HTML.
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

// Atrasa a execução até `delay`ms sem novas chamadas — usado na busca do
// histórico para não disparar uma requisição a cada tecla digitada.
function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}
