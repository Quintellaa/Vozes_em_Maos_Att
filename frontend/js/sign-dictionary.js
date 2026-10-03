/* Sinaliza — dicionário de sinais (MOCK)
   Isso NÃO são sinais reais de Libras — são gestos simplificados (braço levanta,
   pulso balança) só para validar o pipeline de animação: texto → glosa → sequência
   de rotações nas juntas do boneco 3D. Antes de qualquer uso real, isso precisa ser
   substituído por dados de sinais de verdade (capturados ou autorados por alguém
   fluente em Libras).

   Formato de cada keyframe: { t: tempo em ms, rx, ry, rz: rotação em radianos }.
   Cada junta tem sua própria lista de keyframes, ordenada por `t`.
*/
const SIGN_DICTIONARY = {
  DEFAULT: {
    durationMs: 1200,
    keyframes: {
      head: [
        { t: 0, rx: 0, ry: 0, rz: 0 },
        { t: 600, rx: 0, ry: 0.15, rz: 0 },
        { t: 1200, rx: 0, ry: 0, rz: 0 }
      ]
    }
  },

  OI: {
    durationMs: 1600,
    keyframes: {
      rightShoulder: [
        { t: 0, rx: 0, ry: 0, rz: 0 },
        { t: 300, rx: 0, ry: 0, rz: -1.6 },
        { t: 1600, rx: 0, ry: 0, rz: -1.6 }
      ],
      rightElbow: [
        { t: 0, rx: 0, ry: 0, rz: 0 },
        { t: 300, rx: 0, ry: 0, rz: -0.3 },
        { t: 1600, rx: 0, ry: 0, rz: -0.3 }
      ],
      rightWrist: [
        { t: 300, rx: 0, ry: 0, rz: 0 },
        { t: 600, rx: 0, ry: 0.6, rz: 0 },
        { t: 900, rx: 0, ry: -0.6, rz: 0 },
        { t: 1200, rx: 0, ry: 0.6, rz: 0 },
        { t: 1600, rx: 0, ry: 0, rz: 0 }
      ]
    }
  },

  OBRIGADO: {
    durationMs: 1400,
    keyframes: {
      rightShoulder: [
        { t: 0, rx: 0, ry: 0, rz: 0 },
        { t: 400, rx: 0, ry: 0, rz: -1.0 },
        { t: 1000, rx: 0, ry: 0, rz: -0.2 },
        { t: 1400, rx: 0, ry: 0, rz: 0 }
      ],
      rightElbow: [
        { t: 0, rx: 0, ry: 0, rz: 0 },
        { t: 400, rx: 0, ry: 0, rz: -1.4 },
        { t: 1000, rx: 0, ry: 0, rz: -0.6 },
        { t: 1400, rx: 0, ry: 0, rz: 0 }
      ]
    }
  }
};

// MOCK: casamento simples de palavras-chave — não é tradução PT→glosa de verdade.
// Isso deve virar uma etapa própria (NLP) quando o dicionário crescer.
function textToGloss(text) {
  const normalized = text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, ''); // remove acentos

  if (normalized.includes('obrigad')) return 'OBRIGADO';
  if (normalized.includes('ola') || /\boi\b/.test(normalized)) return 'OI';
  return 'DEFAULT';
}
