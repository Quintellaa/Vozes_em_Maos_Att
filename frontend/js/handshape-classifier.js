/* Sinaliza — classificador de configuração de mão (MOCK)
   Usa geometria simples (distância da ponta de cada dedo até o pulso, comparada
   com a distância da base do dedo até o pulso) pra decidir se cada dedo está
   esticado ou dobrado, e com isso reconhece um punhado de formas de mão
   ESTÁTICAS pré-definidas.

   Isso NÃO é reconhecimento de Libras de verdade: um sinal real depende de
   movimento, orientação da mão e localização no corpo — não só uma forma
   parada — e precisa de um modelo treinado com dados reais, que este projeto
   ainda não tem. Isso aqui serve pra provar que o pipeline completo (câmera →
   pontos da mão de verdade → classificação → texto) funciona de ponta a
   ponta, com um lugar claro pra depois trocar por um modelo de verdade.

   Índices dos 21 pontos da mão (convenção do MediaPipe):
   0 = pulso; polegar 1-4, indicador 5-8, médio 9-12, anelar 13-16,
   mindinho 17-20 (o último número de cada grupo é a ponta do dedo).
*/
const FINGER_TIPS = { thumb: 4, index: 8, middle: 12, ring: 16, pinky: 20 };
const FINGER_BASES = { thumb: 2, index: 5, middle: 9, ring: 13, pinky: 17 };

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function isFingerExtended(landmarks, finger) {
  const wrist = landmarks[0];
  const tip = landmarks[FINGER_TIPS[finger]];
  const base = landmarks[FINGER_BASES[finger]];
  // "Esticado" = a ponta está bem mais longe do pulso do que a base do dedo está.
  return distance(tip, wrist) > distance(base, wrist) * 1.15;
}

// Recebe os 21 pontos de uma mão e retorna uma chave de forma de mão, ou null
// se não bater com nenhuma forma conhecida.
function classifyHandshape(landmarks) {
  if (!landmarks) return null;

  const extended = {
    thumb: isFingerExtended(landmarks, 'thumb'),
    index: isFingerExtended(landmarks, 'index'),
    middle: isFingerExtended(landmarks, 'middle'),
    ring: isFingerExtended(landmarks, 'ring'),
    pinky: isFingerExtended(landmarks, 'pinky')
  };
  const extendedCount = Object.values(extended).filter(Boolean).length;

  if (extendedCount >= 4) return 'MAO_ABERTA';
  if (extendedCount === 0) return 'MAO_FECHADA';
  if (extended.index && !extended.middle && !extended.ring && !extended.pinky) return 'APONTANDO';
  if (extended.thumb && !extended.index && !extended.middle && !extended.ring && !extended.pinky) return 'POLEGAR';
  return null;
}

// MOCK: mapeamento provisório forma-de-mão-parada → frase, só pra fechar o
// ciclo da demonstração. Um sinal de Libras de verdade tem movimento.
const HANDSHAPE_PHRASES = {
  MAO_ABERTA: 'Olá, tudo bem?',
  MAO_FECHADA: 'Obrigado.',
  APONTANDO: 'Vem aqui, por favor.',
  POLEGAR: 'Combinado!'
};
