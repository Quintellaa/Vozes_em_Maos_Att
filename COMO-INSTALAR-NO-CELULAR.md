# Vozes em Mãos no celular

O app vira um **aplicativo instalável** (PWA): fica com ícone na tela inicial, abre em tela cheia, sem barra do navegador, e usa a câmera normalmente. Funciona em **Android e iPhone**.

Para isso, o servidor (backend) fica hospedado na nuvem, no **Render** (plano grátis), e ele mesmo entrega o site. O celular só precisa do link.

## 1. Subir o projeto pro GitHub

O Render publica direto de um repositório do GitHub. Envie esta pasta inteira, incluindo os arquivos novos:

- `Dockerfile` e `.dockerignore` (na raiz): montam o servidor da nuvem.
- `render.yaml`: diz ao Render o que criar (o servidor e o banco).
- `frontend/manifest.json`, `frontend/sw.js` e `frontend/img/app-*.png`: o que torna o site instalável.

O `backend/.env` **não** vai pro GitHub (está no `.gitignore`), e é assim mesmo: na nuvem as configurações vêm do `render.yaml`.

## 2. Publicar no Render (uma vez só)

1. Entre em <https://render.com> e crie a conta usando **"Sign in with GitHub"**.
2. No painel, clique em **New → Blueprint**.
3. Escolha o repositório do projeto. O Render lê o `render.yaml` e mostra:
   - `vozes-em-maos` (o servidor);
   - `vozes-em-maos-db` (o banco PostgreSQL).
4. Clique em **Apply** e espere o primeiro deploy, que leva uns 5 a 10 minutos.
5. Abra o serviço `vozes-em-maos`. O link fica no topo, algo como `https://vozes-em-maos.onrender.com`. É esse link que vai pro celular.

Para conferir: `https://SEU-LINK.onrender.com/health` deve mostrar `{"status":"ok"}`.

## 3. Instalar no celular

### Android (Chrome)
1. Abra o link no **Chrome**.
2. Toque no menu **⋮ → "Instalar app"** (em alguns aparelhos aparece "Adicionar à tela inicial").
3. O ícone do mascote aparece na tela inicial.

### iPhone (Safari)
1. Abra o link no **Safari**. Tem que ser o Safari: pelo Chrome do iPhone essa opção não aparece.
2. Toque em **Compartilhar** (o quadrado com a seta) → **"Adicionar à Tela de Início"** → **Adicionar**.

Na primeira vez que abrir o tradutor, o celular pede permissão da câmera: toque em **Permitir**.

### Quer um arquivo .apk (só Android)?
Com o app já no Render, entre em <https://www.pwabuilder.com>, cole o link e clique em **Package for stores → Android**. Ele gera um `.apk` que pode ser instalado no Android (é preciso permitir "instalar apps de fontes desconhecidas"). Por dentro é o mesmo app, então na prática o passo 3 já basta.

## Como atualizar o app

Envie as mudanças pro GitHub. O Render publica sozinho em poucos minutos, e o app instalado pega a versão nova na próxima vez que for aberto. Não precisa reinstalar.

**Retreinou o modelo?** Troque o `MODEL_PATH` no `render.yaml`, além do `backend/.env`.

## Avisos do plano grátis

- **O servidor "dorme" depois de 15 minutos sem uso.** Quando isso acontece, o próximo acesso demora uns 50 segundos. **Antes da apresentação, abra o app uns minutos antes** para ele acordar.
- **O banco grátis do Render vence 30 dias depois de criado.** Depois disso, é só criar outro (ou passar para o plano pago).
- **As contas criadas no PC não existem na nuvem.** São bancos diferentes, então cada pessoa cria a conta de novo pelo app.
- O reconhecimento usa internet: o MediaPipe e o VLibras são baixados de fora, e os sinais são enviados para o servidor.

## Rodando no PC (continua igual)

Live Server na porta 5500/5501 + `uvicorn app.main:app --reload` em `backend/` funcionam como antes. Agora também dá para abrir direto `http://localhost:8000`, porque o backend entrega o site.
