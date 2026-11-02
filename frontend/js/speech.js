/* Sinaliza — síntese de voz (texto → fala)
   Usa a voz do próprio navegador (Web Speech API, speechSynthesis): não precisa
   de servidor, chave de API nem internet depois que a página carregou.

   É isso que fecha o "Libras → texto/FALA" da proposta de valor: a pessoa
   ouvinte não precisa ficar lendo a tela, ela escuta o que foi sinalizado.
*/
const Speech = {
  supported: 'speechSynthesis' in window,

  // Prefere uma voz em português do Brasil; se não houver, usa a padrão.
  _voice() {
    const voices = speechSynthesis.getVoices();
    return voices.find(v => v.lang === 'pt-BR') || voices.find(v => v.lang.startsWith('pt')) || null;
  },

  /** Fala o texto. Retorna false se o navegador não tiver suporte. */
  speak(text) {
    if (!this.supported || !text) return false;
    speechSynthesis.cancel(); // interrompe a fala anterior em vez de enfileirar
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'pt-BR';
    utterance.rate = (typeof Prefs !== 'undefined' && Prefs.get('velocidadeVoz')) || 1;
    const voice = this._voice();
    if (voice) utterance.voice = voice;
    speechSynthesis.speak(utterance);
    return true;
  }
};
