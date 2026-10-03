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
  location.href = 'permissao.html';
}

async function loginWithEmail(name, email, password) {
  try {
    finishLogin(await Api.login(email, password));
  } catch (err) {
    if (err.status !== 401) throw err;
    // MOCK: ainda não existe uma tela de cadastro dedicada. Se o login falhar
    // porque a conta não existe, criamos a conta na hora com os mesmos dados.
    // TODO: remover esse fallback quando houver uma tela de "Criar conta" própria.
    try {
      finishLogin(await Api.register(name, email, password));
    } catch (_registerErr) {
      throw err; // mantém a mensagem original ("e-mail ou senha inválidos")
    }
  }
}

async function loginSocial(provider, name, email) {
  finishLogin(await Api.socialLogin(provider, name, email));
}

// MOCK: usado pelo botão "Começar agora" (index.html) — entra direto com uma
// conta de demonstração, sem pedir credenciais. TODO: remover quando o app
// tiver uma tela de cadastro real.
async function instantDemoLogin() {
  try {
    await loginSocial('google', DEFAULT_USER.name, DEFAULT_USER.email);
  } catch (err) {
    toast(err.message);
  }
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
