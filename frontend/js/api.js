/* Sinaliza — cliente HTTP para o backend (FastAPI)
   Isola fetch/JSON/erros num só lugar, para que session.js e history.js só
   precisem chamar métodos com nome (Api.login, Api.createHistory...) sem
   se preocupar com header, status code ou parsing.
*/

// Quando o site é aberto pelo Live Server (portas 5500-5502) ou direto do arquivo,
// o backend está à parte, na porta 8000. Em qualquer outro caso (servidor na nuvem,
// app instalado no celular), o próprio backend entrega o site: mesma origem.
const API_BASE_URL = location.protocol === 'file:' || /^550\d$/.test(location.port)
  ? `http://${location.hostname || 'localhost'}:8000`
  : location.origin;

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function apiRequest(path, { method = 'GET', body, auth = false } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined
    });
  } catch (networkError) {
    // fetch rejeita a Promise em erro de rede (servidor fora do ar, CORS bloqueado etc.)
    throw new ApiError(0, 'Não foi possível conectar ao servidor. Verifique se o backend está rodando.');
  }

  if (response.status === 204) return null; // sem corpo (ex.: DELETE)

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    // Erros de validação do FastAPI (422) trazem `detail` como lista, não string.
    const detail = typeof data?.detail === 'string' ? data.detail : 'Ocorreu um erro inesperado.';
    throw new ApiError(response.status, detail);
  }

  return data;
}

const Api = {
  register: (name, email, password) =>
    apiRequest('/auth/register', { method: 'POST', body: { name, email, password } }),

  login: (email, password) =>
    apiRequest('/auth/login', { method: 'POST', body: { email, password } }),

  socialLogin: (provider, name, email) =>
    apiRequest('/auth/social', { method: 'POST', body: { provider, name, email } }),

  me: () => apiRequest('/auth/me', { auth: true }),

  // Perfil: mande só os campos que mudaram ({ name }, { handle } ou os dois).
  updateMe: fields => apiRequest('/auth/me', { method: 'PATCH', body: fields, auth: true }),

  // Números do perfil: { translations, lessons, badges }
  myStats: () => apiRequest('/auth/me/stats', { auth: true }),

  // Foto de perfil: dataUrl = "data:image/jpeg;base64,..." (já recortada em js/perfil.js)
  setAvatar: dataUrl => apiRequest('/auth/me/avatar', { method: 'PUT', body: { image: dataUrl }, auth: true }),
  deleteAvatar: () => apiRequest('/auth/me/avatar', { method: 'DELETE', auth: true }),

  changePassword: (currentPassword, newPassword) =>
    apiRequest('/auth/password', {
      method: 'POST',
      body: { current_password: currentPassword, new_password: newPassword },
      auth: true
    }),

  listHistory: (queryString = '') => apiRequest(`/history${queryString}`, { auth: true }),

  createHistory: (type, text) =>
    apiRequest('/history', { method: 'POST', body: { type, text }, auth: true }),

  toggleFavorite: id => apiRequest(`/history/${id}/favorite`, { method: 'PATCH', auth: true }),

  deleteHistoryEntry: id => apiRequest(`/history/${id}`, { method: 'DELETE', auth: true }),

  clearHistory: () => apiRequest('/history', { method: 'DELETE', auth: true }),

  // frames: [{ pose: [33 pontos {x,y,z}] | null,
  //            hands: { left: [21 pontos] | null, right: [21 pontos] | null } }, ...]
  // (formato "pose-hands-v1", montado em recognizer.js)
  predictSign: frames => apiRequest('/recognition/predict', { method: 'POST', body: { frames }, auth: true }),

  recognitionInfo: () => apiRequest('/recognition/info', { auth: true }),

  // ---- Comunidades ----
  // filtros: { search, category, joined } — todos opcionais
  listCommunities: (filtros = {}) => {
    const qs = new URLSearchParams(Object.entries(filtros).filter(([, v]) => v !== undefined && v !== '')).toString();
    return apiRequest(`/communities${qs ? '?' + qs : ''}`, { auth: true });
  },
  getCommunity: id => apiRequest(`/communities/${id}`, { auth: true }),
  createCommunity: dados => apiRequest('/communities', { method: 'POST', body: dados, auth: true }),
  joinCommunity: id => apiRequest(`/communities/${id}/join`, { method: 'POST', auth: true }),
  leaveCommunity: id => apiRequest(`/communities/${id}/join`, { method: 'DELETE', auth: true }),
  listPosts: id => apiRequest(`/communities/${id}/posts`, { auth: true }),
  createPost: (id, text) => apiRequest(`/communities/${id}/posts`, { method: 'POST', body: { text }, auth: true }),
  deletePost: (id, postId) => apiRequest(`/communities/${id}/posts/${postId}`, { method: 'DELETE', auth: true })
};
