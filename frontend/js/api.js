/* Sinaliza — cliente HTTP para o backend (FastAPI)
   Isola fetch/JSON/erros num só lugar, para que session.js e history.js só
   precisem chamar métodos com nome (Api.login, Api.createHistory...) sem
   se preocupar com header, status code ou parsing.
*/

// Ajuste aqui se o backend rodar em outra porta/host (ex.: quando for para produção).
const API_BASE_URL = 'http://localhost:8000';

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

  listHistory: (queryString = '') => apiRequest(`/history${queryString}`, { auth: true }),

  createHistory: (type, text) =>
    apiRequest('/history', { method: 'POST', body: { type, text }, auth: true }),

  toggleFavorite: id => apiRequest(`/history/${id}/favorite`, { method: 'PATCH', auth: true }),

  deleteHistoryEntry: id => apiRequest(`/history/${id}`, { method: 'DELETE', auth: true }),

  clearHistory: () => apiRequest('/history', { method: 'DELETE', auth: true }),

  // frames: [{ hand: [21 pontos {x,y,z}] | null }, ...]
  predictSign: frames => apiRequest('/recognition/predict', { method: 'POST', body: { frames }, auth: true }),

  recognitionInfo: () => apiRequest('/recognition/info', { auth: true })
};
