# Relatório de treino — reconhecimento de Libras

- Data: 02/11/2026 15:37
- Amostras: 582 · Sinais: 19 · Pessoas: 6 (jb, kathleen, librasil_a1, librasil_a2, librasil_a3, victor)
- Avaliação: pessoa nova (treina sem a pessoa, testa nela)
- Algoritmo escolhido: **LOGREG**

## Acurácia

| Algoritmo | Acurácia |
|---|---|
| RF | 42.6% |
| SVM | 38.3% |
| KNN | 43.5% |
| ET | 41.2% |
| LOGREG | 44.3% |

## Por pessoa (testando em quem ficou fora do treino)

| Pessoa | Acurácia |
|---|---|
| jb | 54.9% |
| kathleen | 39.0% |
| librasil_a1 | 44.4% |
| librasil_a2 | 88.9% |
| librasil_a3 | 33.3% |
| victor | 35.8% |

## Por sinal

| Sinal | Acerto |
|---|---|
| até mais | 0.0% |
| boa noite | 0.0% |
| boa tarde | 0.0% |
| bom dia | 0.0% |
| meu nome é | 0.0% |
| olá | 0.0% |
| olá, tudo bem? | 0.0% |
| qual seu nome? | 0.0% |
| tudo bem | 0.0% |
| ajuda | 4.3% |
| água | 8.7% |
| banheiro | 17.4% |
| obrigado | 34.8% |
| por favor | 44.2% |
| tchau | 62.5% |
| sim | 70.8% |
| desculpa | 90.7% |
| oi | 91.2% |
| não | 94.1% |

## Confusões mais comuns

| Era | Ele achou que era | Vezes |
|---|---|---|
| tudo bem | desculpa | 20 |
| até mais | por favor | 20 |
| água | não | 20 |
| olá | tchau | 19 |
| boa noite | banheiro | 18 |
| tchau | olá | 15 |
| meu nome é | banheiro | 15 |
| sim | não | 13 |
| olá, tudo bem? | oi | 13 |
| por favor | até mais | 12 |

Se dois sinais se confundem muito, considere trocar um deles por um sinal mais diferente.

## Matriz de confusão (linha = sinal feito, coluna = sinal reconhecido)

| | AGUA | AJUDA | ATE_MAIS | BANHEIRO | BOA_NOITE | BOA_TARDE | BOM_DIA | DESCULPA | MEU_NOME | NAO | OBRIGADO | OI | OLA | OLA_TUDO_BEM | POR_FAVOR | QUAL_SEU_NOME | SIM | TCHAU | TUDO_BEM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **AGUA** | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **AJUDA** | 0 | 1 | 5 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 10 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| **ATE_MAIS** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 | 0 |
| **BANHEIRO** | 0 | 10 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 5 | 1 | 0 |
| **BOA_NOITE** | 0 | 2 | 0 | 18 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **BOA_TARDE** | 0 | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 12 |
| **BOM_DIA** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| **DESCULPA** | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 39 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 0 | 0 |
| **MEU_NOME** | 0 | 0 | 0 | 15 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **NAO** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 64 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 0 | 1 |
| **OBRIGADO** | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 12 | 0 | 0 | 0 | 0 |
| **OI** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 62 | 1 | 3 | 0 | 0 | 0 | 0 | 0 |
| **OLA** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 0 |
| **OLA_TUDO_BEM** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **POR_FAVOR** | 0 | 2 | 12 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 19 | 0 | 0 | 8 | 0 |
| **QUAL_SEU_NOME** | 0 | 1 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 2 | 1 | 0 | 6 | 0 | 4 | 0 | 0 | 0 | 0 |
| **SIM** | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 34 | 0 | 0 |
| **TCHAU** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | 0 | 25 | 0 |
| **TUDO_BEM** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
