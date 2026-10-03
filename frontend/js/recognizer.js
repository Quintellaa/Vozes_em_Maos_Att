/* Sinaliza — reconhecimento de Libras (câmera → texto)
   MOCK: hoje simula frases fixas com timers, só para validar o fluxo de UI.
   Quando o modelo de reconhecimento estiver pronto, reimplemente start()/stop()
   mantendo a mesma assinatura (onPhrase/onError) — assim pages.js não precisa mudar.
*/
const RECOGNITION_INTERVAL_MS = 6000;
const RECOGNITION_FIRST_DELAY_MS = 2500;

const Recognizer = {
  _stream: null,

  async start(videoEl, { onPhrase, onError } = {}) {
    if (!navigator.mediaDevices) {
      onError?.('Câmera não suportada neste navegador.');
      return;
    }
    try {
      this._stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      videoEl.srcObject = this._stream;

      // TODO: substituir a simulação abaixo pela saída real do modelo de reconhecimento de Libras
      // (ex.: enviar frames para um WebSocket/worker e chamar onPhrase(texto) a cada sinal reconhecido).
      const mockPhrases = [
        'Olá, eu gostaria de saber onde fica a saída mais próxima?',
        'Obrigado pela informação.',
        'Posso ajudar com mais alguma coisa?'
      ];
      let i = 0;
      const emitNext = () => {
        onPhrase?.(mockPhrases[i]);
        if (++i < mockPhrases.length) setTimeout(emitNext, RECOGNITION_INTERVAL_MS);
      };
      setTimeout(emitNext, RECOGNITION_FIRST_DELAY_MS);
    } catch (err) {
      onError?.('Não foi possível acessar a câmera. Libere a permissão nas configurações do navegador.');
    }
  },

  stop() {
    this._stream?.getTracks().forEach(track => track.stop());
    this._stream = null;
  }
};
