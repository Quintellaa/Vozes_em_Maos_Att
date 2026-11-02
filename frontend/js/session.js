/* Sinaliza — sessão do usuário (conectada ao backend real via api.js)
   Guardamos o token JWT (fonte da verdade da sessão) e uma cópia do usuário
   (só para exibir nome/handle sem esperar uma chamada de rede a cada tela).
*/
const TOKEN_KEY = 'token';
const USER_KEY = 'user';
const DEFAULT_USER = { name: 'Gabriel Silva', email: 'gabriel.silva@gmail.com' };

function getToken() {
  return Storage.get(TOKEN_KEY, null);
}

function getCurrentUser() {
  return Storage.get(USER_KEY, null);
}

function persistSession({ access_token, user }) {
  const savedToken = Storage.set(TOKEN_KEY, access_token);
  const savedUser = Storage.set(USER_KEY, user);
  return savedToken && savedUser;
}

function finishLogin(session) {
  if (!persistSession(session)) {
    toast('Não foi possível salvar sua sessão neste navegador. Verifique o modo privado ou o bloqueio de cookies.');
    return;
  }
  // Quem já respondeu sobre a câmera neste aparelho vai direto para o Tradutor.
  location.href = Storage.get('cam') ? 'tradutor.html' : 'permissao.html';
}

async function loginWithEmail(email, password) {
  finishLogin(await Api.login(email, password));
}

async function registerAccount(name, email, password) {
  finishLogin(await Api.register(name, email, password));
}

async function loginSocial(provider, name, email) {
  finishLogin(await Api.socialLogin(provider, name, email));
}

async function refreshCurrentUser() {
  const freshUser = await Api.me();
  Storage.set(USER_KEY, freshUser);
  return freshUser;
}

function logout() {
  Storage.remove(TOKEN_KEY);
  Storage.remove(USER_KEY);
  location.href = 'index.html';
}

// Bio (e, em versões antigas, a foto) ficam neste aparelho, separadas por conta.
function getLocalProfile(user = getCurrentUser()) {
  return Storage.get('perfilLocal:' + (user?.id ?? 'anon'), {}) || {};
}

// Endereço completo da foto de um usuário (vinda do servidor), ou null.
function avatarSrc(user) {
  return user?.avatar_url ? API_BASE_URL + user.avatar_url : null;
}

// A foto antes ficava só no navegador. Se ainda houver uma foto antiga aqui e a conta
// não tiver foto no servidor, envia uma vez — assim ela passa a aparecer para todos.
async function syncLocalPhoto(user) {
  const local = getLocalProfile(user);
  if (!local.foto || !user?.id) return user;
  let atualizado = user;
  if (!user.avatar_url) {
    try {
      atualizado = await Api.setAvatar(local.foto);
      Storage.set(USER_KEY, atualizado);
    } catch (err) {
      return user; // tenta de novo numa próxima vez
    }
  }
  const { foto, ...resto } = local;
  Storage.set('perfilLocal:' + user.id, resto);
  return atualizado;
}

// Desenha o avatar do usuário (foto, ou iniciais se não tiver foto) em todo
// elemento com data-ini — ex.: o círculo no topo do Tradutor.
function renderUserAvatar(root = document) {
  const user = getCurrentUser() || DEFAULT_USER;
  const foto = avatarSrc(user) || getLocalProfile(user).foto;
  $$('[data-ini]', root).forEach(el => {
    if (foto) {
      el.innerHTML = '';
      const img = document.createElement('img');
      img.src = foto;
      img.alt = '';
      img.className = 'ava-img';
      el.appendChild(img);
    } else {
      el.textContent = initials(user.name || DEFAULT_USER.name);
    }
    if (el.hasAttribute('aria-label') && el.getAttribute('href')) el.setAttribute('aria-label', `Perfil de ${user.name}`);
  });
}

function initials(name) {
  return name.split(/\s+/).map(word => word[0]).slice(0, 2).join('').toUpperCase();
}

// Trata erros de chamadas à API de forma consistente em toda a aplicação:
// sessão inválida/expirada desloga e volta para o início; qualquer outro erro vira um toast.
function reportApiError(err) {
  if (err instanceof ApiError && err.status === 401) {
    Storage.remove(TOKEN_KEY);
    Storage.remove(USER_KEY);
    location.replace('index.html');
    return;
  }
  toast(err?.message || 'Ocorreu um erro. Tente novamente.');
}

// Guarda de rota: páginas marcadas com data-auth exigem um token salvo.
// (Isso não valida se o token ainda é aceito pelo servidor — se estiver expirado,
// a primeira chamada à API vai falhar com 401 e reportApiError cuida do logout.)
if (document.body.hasAttribute('data-auth') && !getToken()) {
  location.replace('index.html');
}
