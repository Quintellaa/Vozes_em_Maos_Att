/* Sinaliza — avatar de Libras (texto → sinais).
   Ponto único de acesso: pages.js só conhece Avatar.play(el, texto).

   Os movimentos vêm de gravações reais (ver js/sign-animations.js). O avatar
   reproduz a TRAJETÓRIA DOS BRAÇOS do sinal, mas não a configuração dos dedos
   nem a expressão facial — que em Libras distinguem sinais. É uma aproximação,
   e precisa de validação de alguém fluente antes de qualquer uso real.
*/
const Avatar = {
  _initialized: false,

  _ensureInit(el) {
    if (this._initialized) return;
    Avatar3D.init(el.querySelector('.face3d'));
    this._initialized = true;
  },

  /** Retorna { known: boolean, gloss: string|null } pra tela saber o que dizer. */
  play(el, text, { onEnd } = {}) {
    this._ensureInit(el);

    const gloss = textToGloss(text);
    if (!gloss) {
      return { known: false, gloss: null };
    }

    Avatar3D.play(SIGN_ANIMATIONS[gloss], { onEnd });
    return { known: true, gloss };
  }
};
