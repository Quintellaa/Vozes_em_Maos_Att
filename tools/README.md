# Treino do reconhecimento de Libras

Fluxo completo, do zero ao modelo rodando no app.

## 1. Escolher os sinais

Edite `frontend/js/recording-config.js`. A lista que está lá é só uma **sugestão** —
validem com alguém fluente em Libras antes de gravar.

## 2. Gravar (cada pessoa do grupo)

1. Suba o backend e abra o app no Live Server (ver `backend/README.md`).
2. Abra **direto pelo endereço** `.../frontend/gravar.html` (ex.: `http://127.0.0.1:5501/frontend/gravar.html`).
   É uma ferramenta **só da equipe**: de propósito, não tem link pra ela no app.
   O usuário final nunca grava nada — ele usa o modelo que vocês treinaram.
3. Coloque seu nome, escolha o sinal e clique em **Iniciar câmera**.
   Espere o aviso no canto da câmera ficar **verde** (enquadramento bom) antes de começar.
   Use **"Ver como se faz o sinal"** pra conferir o sinal no avatar do VLibras.
4. Faça o sinal e **abaixe as mãos até sumirem da câmera**. Repita até completar.
5. O arquivo `.json` é salvo sozinho em Downloads. Passe pro próximo sinal.

**Meta:** cada pessoa grava **20 repetições de cada sinal**, em **2 sessões**
(lugares/luz diferentes — ex.: 10 em casa, 10 na faculdade).

Juntem todos os arquivos em `dados/gravacoes/`.

### Reforço: vídeos da V-LIBRASIL (UFPE)

9 sinais da lista existem na base pública V-LIBRASIL (3 intérpretes, 1 vídeo cada):
oi, sim, não, obrigado, ajuda, banheiro, água, desculpa, por favor.

1. Na raiz: `py -3.14 tools/baixar_librasil.py` → baixa pra `dados/librasil_videos/`.
2. Em `gravar.html` → **Importar vídeo**, selecione todos de uma vez. O sinal e a
   pessoa saem do nome do arquivo (não precisa preencher o nome). Demora uns
   10–40 s por vídeo: a tela analisa quadro a quadro.
3. Mova os `.json` de Downloads pra `dados/gravacoes/`.

É só reforço (3 exemplos por sinal): o grupo ainda grava esses sinais.
Licença: pesquisa/educação, citando a dissertação de A. J. Rodrigues (UFPE, 2021);
**não** redistribua os vídeos (a pasta já está no `.gitignore`).

## 3. Treinar

Dentro de `backend`, com o `.venv` ativado:

```bash
python ../tools/train_and_export.py
```

Ele mostra quantas amostras tem por pessoa/sinal, mede a acurácia **numa pessoa que
ficou fora do treino** (o número honesto), escolhe o melhor algoritmo e salva:

- `backend/models/libras_grupo.joblib` — o modelo
- `tools/relatorio_treino.md` — acurácia por pessoa, por sinal e confusões
- `tools/relatorio_treino.png` — matriz de confusão (pra slide)

## 4. Usar no app

No `backend/.env`:

```
MODEL_PATH=models/libras_grupo.joblib
```

Reinicie a API (Ctrl+C e `uvicorn app.main:app --reload` de novo).

## Dicas de gravação (o que mais ajuda o reconhecimento)

- Grave **pessoas diferentes**: com 1 pessoa só, o relatório parece ótimo e o app erra em outras pessoas.
- Deixe a **mão bem visível** (palma/dedos virados pra câmera quando o sinal permitir), com boa luz e fundo liso.
- Faça o sinal em **velocidade normal**; o modelo já tolera um pouco mais rápido/devagar.
- Se uma amostra for **descartada**, leia o motivo na tela e repita: amostra ruim piora o modelo.
- Depois de treinar, olhe o relatório: se um sinal tem acerto baixo, **grave mais repetições dele**.

## Se a acurácia ficar baixa

- Veja no relatório **quais sinais se confundem** e troque um deles por um mais diferente.
- Veja **qual pessoa** vai pior: pode ser enquadramento/luz nas gravações dela.
- Mais variedade ajuda mais que mais repetições iguais.
- Meta do grupo: **≥ 85%** em pessoa nova. Abaixo disso, cortem pra 8 sinais.
