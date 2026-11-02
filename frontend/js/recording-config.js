/* Sinaliza — QUAIS SINAIS o grupo vai gravar e treinar.

   ⚠️ ESTA LISTA É UMA SUGESTÃO. Antes de gravar, validem com alguém fluente em
   Libras (intérprete, professor, FENEIS): o sinal certo de cada palavra e se
   vocês estão fazendo do jeito certo. Gravar um sinal errado ensina o modelo
   errado — e engana quem depender do app.

   Critérios pra escolher:
     - úteis numa conversa do dia a dia;
     - BEM DIFERENTES entre si (lugar do corpo, formato da mão, movimento).
       Sinais parecidos são o que mais derruba a acurácia.

   gloss: código do sinal — MAIÚSCULAS, sem acento, sem espaço (vira nome de arquivo)
   word:  como a palavra aparece na tela e é falada pela voz

   Frases (QUAL_SEU_NOME, PRECISO_AJUDA...) são gravadas como UM clipe só:
   faça a frase inteira sem abaixar as mãos no meio, e só abaixe no fim.
*/
const SIGNS_TO_RECORD = [
  { gloss: 'OI',            word: 'oi' },
  { gloss: 'OLA',           word: 'olá' },
  { gloss: 'TCHAU',         word: 'tchau' },
  { gloss: 'ATE_MAIS',      word: 'até mais' },
  { gloss: 'SIM',           word: 'sim' },
  { gloss: 'NAO',           word: 'não' },
  { gloss: 'TUDO_BEM',      word: 'tudo bem' },
  { gloss: 'OLA_TUDO_BEM',  word: 'olá, tudo bem?' },
  { gloss: 'QUAL_SEU_NOME', word: 'qual seu nome?' },
  { gloss: 'MEU_NOME',      word: 'meu nome é' },
  { gloss: 'OBRIGADO',      word: 'obrigado' },
  { gloss: 'PRECISO_AJUDA', word: 'preciso de ajuda' },
  { gloss: 'AJUDA',         word: 'ajuda' },
  { gloss: 'BANHEIRO',      word: 'banheiro' },
  { gloss: 'AGUA',          word: 'água' },
  { gloss: 'DESCULPA',      word: 'desculpa' },
  { gloss: 'POR_FAVOR',     word: 'por favor' },
  { gloss: 'BOM_DIA',       word: 'bom dia' },
  { gloss: 'BOA_TARDE',     word: 'boa tarde' },
  { gloss: 'BOA_NOITE',     word: 'boa noite' }
];

const DEFAULT_REPETITIONS = 20; // por pessoa, por sinal, por sessão
