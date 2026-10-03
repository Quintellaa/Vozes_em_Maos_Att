/* Sinaliza — histórico de traduções (agora persistido no backend, via api.js) */

function getHistory({ type, favorite, search } = {}) {
  const params = new URLSearchParams();
  if (type) params.set('type', type);
  if (favorite !== undefined) params.set('favorite', String(favorite));
  if (search) params.set('search', search);
  const queryString = params.toString();
  return Api.listHistory(queryString ? `?${queryString}` : '');
}

function addHistoryEntry(type, text) {
  return Api.createHistory(type, text);
}

function toggleHistoryFavorite(id) {
  return Api.toggleFavorite(id);
}

function clearHistory() {
  return Api.clearHistory();
}
