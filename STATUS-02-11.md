# Vozes em Mãos: status de 02/11

## O que mudou
- **Gravações novas do João (jb):**
  - 20 repetições de cada sinal: oi (×2), não, tchau, desculpa, obrigado, por favor, bom dia, boa tarde e boa noite;
  - a qualidade foi conferida e todas foram aproveitadas.
- **Sinais novos na lista:** bom dia, boa tarde e boa noite (`frontend/js/recording-config.js`).
- **Tela de gravação:** o avatar do VLibras não fica mais por cima da câmera.
  - Ele só aparece com "Ver como se faz o sinal" aberto.
  - Clicar em "Iniciar câmera" fecha a referência sozinho.
- **Modelo novo:** `backend/models/libras_grupo_2026-11-02.joblib`, já apontado no `backend/.env`.
  - Treinado com 58 arquivos, 19 sinais e 6 pessoas.
  - Venceu a regressão logística (LOGREG).
  - O modelo anterior (`libras_grupo_2026-11-01.joblib`) continua na pasta.

## Resultado do treino (acerto em pessoa que o modelo nunca viu)
- **Geral: 44%.** No treino de 01/11 era 33%.
- **Sinais gravados por 2+ pessoas:**

  | Sinal | Acerto |
  |---|---|
  | não | 94% |
  | oi | 91% |
  | desculpa | 91% |
  | sim | 71% |
  | tchau | 63% |
  | por favor | 44% |
  | obrigado | 35% |

- **Sinais gravados por 1 pessoa só ficam com 0%.** Com uma pessoa só, não dá pra testar em pessoa nova. Isso não quer dizer que o app erra esses sinais com quem gravou; quer dizer que ele ainda não aprendeu o sinal "em geral".
- O relatório completo está em `tools/relatorio_treino.md`, e a imagem em `relatorio_treino.png`.

## Próximo passo: cobrir cada sinal com pelo menos 2 pessoas

| Quem gravou | Sinais | Quem precisa gravar |
|---|---|---|
| Só o Victor | tudo bem, olá tudo bem?, qual seu nome?, meu nome é, água, ajuda | João ou Kathleen |
| Só a Kathleen | olá, até mais, banheiro | João ou Victor |
| Só o João | bom dia, boa tarde, boa noite | Victor ou Kathleen |
| Ninguém | preciso de ajuda | — |

Como gravar e treinar: veja o `STATUS-17-10.md` e o `tools/README.md`. Depois de treinar, troque o `MODEL_PATH` no `backend/.env` e **reinicie o servidor**.

Faltam ~13 dias. Se não der pra cobrir tudo, na apresentação foquem nos sinais que funcionam bem.
