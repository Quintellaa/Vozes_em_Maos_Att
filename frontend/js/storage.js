/* Sinaliza — camada de persistência (localStorage)
   Cada método retorna um resultado explícito (valor/booleano) em vez de falhar
   silenciosamente, para que quem chama possa reagir a uma gravação que não
   funcionou (ex.: modo privado do navegador, cota de storage excedida).
*/
const STORAGE_PREFIX = 'sinaliza:';

const Storage = {
  get(key, fallback = null) {
    try {
      const raw = localStorage.getItem(STORAGE_PREFIX + key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (err) {
      console.warn(`[Storage] Falha ao ler "${key}":`, err);
      return fallback;
    }
  },

  set(key, value) {
    try {
      localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value));
      return true;
    } catch (err) {
      console.warn(`[Storage] Falha ao gravar "${key}":`, err);
      return false;
    }
  },

  remove(key) {
    try {
      localStorage.removeItem(STORAGE_PREFIX + key);
      return true;
    } catch (err) {
      console.warn(`[Storage] Falha ao remover "${key}":`, err);
      return false;
    }
  }
};
