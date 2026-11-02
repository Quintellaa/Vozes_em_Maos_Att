/* Sinaliza — glosa (código do sinal) → palavra em português.

   O modelo de reconhecimento devolve uma GLOSA: o código do sinal, em
   maiúsculas e sem acento ("AGUA", "OBRIGADO"). Pra mostrar e falar, a gente
   precisa da palavra de verdade ("água").

   Modelos treinados com tools/train_and_export.py já trazem a palavra de cada
   sinal (a API devolve no campo `word`). Este mapa fica só como reserva, pro
   modelo antigo do MINDS-Libras, que não trazia as palavras.
*/
const GLOSS_WORDS = {
  MACA: 'maçã',
  AMERICA: 'América'
};

/** "MACA" → "maçã", "BANHEIRO" → "banheiro". */
function glossToWord(gloss) {
  return GLOSS_WORDS[gloss] || String(gloss).toLowerCase();
}
