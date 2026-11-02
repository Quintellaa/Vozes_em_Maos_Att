# Vozes em Mãos: status de 17/10

## O que mudou nesta versão
- **Tradutor:** a caixa de transcrição ficou compacta. A lista de sinais virou um chip "Sinais" no canto.
- **Reconhecimento:**
  - os pontos da câmera são corrigidos pela proporção da imagem, então celular em pé e webcam deitada dão o mesmo resultado;
  - o cálculo novo (`pose-hands-v2`) não depende de qual mão faz o sinal, o que cobre canhotos e vídeo espelhado.
- **Treino** (`tools/train_and_export.py`):
  - testa 4 modelos (RF, SVM, KNN, LogReg) e fica com o melhor;
  - ignora gravações antigas, sem a correção de proporção.
- **Ferramenta de gravação** (`frontend/gravar.html`, só pra equipe, sem link no app):
  - grava pela webcam ou **importa vídeos gravados no celular**;
  - quando descarta uma repetição, diz o motivo.
- **Modelo de teste:** `backend/models/libras_grupo.joblib` foi treinado só com o João, 5 repetições de oi, sim e não. O `backend/.env` já aponta pra ele.
  - O modelo antigo (`libras_pose_hands.joblib`, 20 sinais do banco público MINDS) continua na pasta. Pra voltar a ele, troque o `MODEL_PATH` no `.env`.

## Como rodar
1. Na pasta `backend`, rode `py -3.14 -m uvicorn app.main:app --reload`. Espere aparecer "Application startup complete".
2. Ligue o Live Server ("Go Live") e abra `http://127.0.0.1:5501/frontend/tradutor.html`.
3. Mudou o `.env` ou o modelo? **Feche o servidor (Ctrl+C) e rode de novo.** Se um servidor antigo ficar aberto, o app continua usando o modelo velho.
   - Pra conferir, abra o chip "Sinais": ele mostra os sinais do modelo carregado.

## Próximo passo: gravar os 10 sinais
1. Abra `http://127.0.0.1:5501/frontend/gravar.html`.
2. Preencha o seu nome, escolha o sinal e coloque **20** em "Repetições".
3. Antes de gravar, **feche** o "Ver como se faz o sinal" (por enquanto o avatar fica por cima da câmera).
4. Fique longe da câmera: os ombros devem ficar perto do meio da imagem.
5. Faça o sinal, **abaixe as mãos até sumirem da imagem** e repita.
6. O `.json` vai pra pasta Downloads. Mova pra `dados/gravacoes`.
7. Depois de gravar, treine: na raiz do projeto, rode `py -3.14 tools/train_and_export.py` e reinicie o servidor.

Precisamos de **pelo menos 2 pessoas** gravando. Com uma só, o modelo não aprende a reconhecer gente que ele nunca viu, e a acurácia do relatório parece melhor do que é.

Os sinais estão em `frontend/js/recording-config.js`: oi, obrigado, sim, não, ajuda, banheiro, água, desculpa, por favor e tudo bem. Validem com alguém fluente em Libras antes de gravar.

## Pendências conhecidas
- O avatar do VLibras na tela de gravação fica por cima da câmera depois de aberto.
- Ainda não testamos ao vivo o modelo de teste: o servidor antigo continuou rodando.
- Antes de subir pro GitHub ou entregar:
  - apagar `backend/.env`, que tem um segredo de exemplo (use o `.env.example`);
  - tirar `gravar.html`, `gravar.js` e `dados/`, que não fazem parte do app final.
  - Os bancos `.db` não vão neste zip: a API cria um vazio sozinha, e cada um cria a própria conta.
