/* Sinaliza — avatar de Libras (texto → sinais)
   Ponto único de acesso ao avatar: pages.js só conhece Avatar.play(el, text).
   Por baixo, hoje isso aciona o boneco 3D (Three.js) + o dicionário de sinais
   simplificado (avatar-3d.js / sign-dictionary.js). Quando isso virar um modelo
   3D de verdade com sinais reais, só o que está DENTRO deste arquivo muda.
*/
const Avatar = {
  _initialized: false,

  play(el, text, { onStart, onEnd } = {}) {
    if (!this._initialized) {
      Avatar3D.init(el.querySelector('.face3d'));
      this._initialized = true;
    }
    onStart?.();
    Avatar3D.play(textToGloss(text), { onEnd });
  }
};
