/* Sinaliza — mapeamento texto digitado → sinal do avatar.

   As animações em si vêm de js/sign-animations.js, gerado por
   tools/export_avatar_signs.py a partir de gravações REAIS do MINDS-Libras.
   Aqui só traduzimos o que o usuário digitou para a chave do sinal.

   LIMITE IMPORTANTE: o avatar só conhece os 20 sinais do dataset. Para qualquer
   outra palavra, devolvemos null e o app AVISA que não sabe — de propósito.
   Mostrar um sinal errado é pior que não mostrar nada: a pessoa que depende de
   Libras não tem como saber que viu algo incorreto.
*/

// Tira acentos, pontuação e caixa, pra "Maçã!" casar com "MACA".
function normalizeWord(text) {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, '')
    .trim();
}

// Palavras diferentes que levam ao mesmo sinal do dataset.
const WORD_ALIASES = {
  maca: 'MACA', maçã: 'MACA', maa: 'MACA',
  banheiro: 'BANHEIRO', toalete: 'BANHEIRO',
  '5': 'CINCO'
};

/** Retorna a chave do sinal, ou null se o avatar não conhecer a palavra. */
function textToGloss(text) {
  const normalized = normalizeWord(text);
  if (!normalized) return null;

  const available = typeof SIGN_ANIMATIONS === 'undefined' ? {} : SIGN_ANIMATIONS;

  // Procura palavra por palavra: assim "quero maçã" encontra MACA.
  for (const word of normalized.split(/\s+/)) {
    const direct = word.toUpperCase();
    if (available[direct]) return direct;
    const alias = WORD_ALIASES[word];
    if (alias && available[alias]) return alias;
  }
  return null;
}

/** Lista de palavras que o avatar sabe sinalizar (pra mostrar ao usuário). */
function knownSigns() {
  return typeof SIGN_ANIMATIONS === 'undefined' ? [] : Object.keys(SIGN_ANIMATIONS).sort();
}
