# Como configurar o e-mail do "Esqueci a senha" (pelo seu Gmail)

O plano grátis do Render não deixa o app enviar e-mail direto pelo Gmail (bloqueia o SMTP).
A saída é um pequeno script do Google (Google Apps Script, de graça) que envia pela sua conta:
o app chama o script pela internet e o script manda o e-mail.

Leva uns 10 minutos. Limite: cerca de **100 e-mails por dia**.

## 1. Escolha um segredo

Invente uma senha longa, só com letras e números (ex.: `vozes2026` + umas 20 letras aleatórias).
Ela vai em dois lugares: no script (passo 2) e no Render (passo 4). **Tem que ser igual nos dois.**
Não use a senha do seu Gmail.

## 2. Crie o script

1. Entre em **https://script.google.com** com o Gmail que vai enviar os e-mails.
2. Clique em **Novo projeto**. No topo, troque "Projeto sem título" por `Vozes em Mãos - E-mail`.
3. Apague tudo o que estiver no editor e cole o conteúdo de [`tools/email-gmail/Codigo.gs`](tools/email-gmail/Codigo.gs).
4. Na linha `const SEGREDO = 'TROQUE-POR-UMA-SENHA-LONGA';`, troque o texto entre aspas pelo seu segredo.
5. Clique no ícone de disquete (**Salvar**).

## 3. Autorize e implante

1. Na barra de cima, escolha a função **testarEnvio** e clique em **Executar**.
2. O Google pede autorização: **Revisar permissões** → escolha sua conta.
   Vai aparecer "O Google não verificou este app" (é normal, o app é seu):
   clique em **Avançado** → **Acessar Vozes em Mãos - E-mail (não seguro)** → **Permitir**.
3. Confira seu Gmail: deve chegar "Teste do Vozes em Mãos".
4. Clique em **Implantar** → **Nova implantação**.
5. Na engrenagem ao lado de "Selecione o tipo", escolha **App da Web** e preencha:
   - **Executar como:** Eu
   - **Quem pode acessar:** Qualquer pessoa ← importante
6. Clique em **Implantar** e copie a **URL do app da Web** (termina em `/exec`).

Para conferir, abra essa URL no navegador: deve aparecer `"ok":true` e "Script de e-mail do Vozes em Mãos no ar".

## 4. Configure no Render

No painel do Render, abra o serviço **vozes-em-maos** → **Environment** → adicione:

| Nome | Valor |
|---|---|
| `GMAIL_SCRIPT_URL` | a URL copiada no passo 3 (termina em `/exec`) |
| `GMAIL_SCRIPT_SECRET` | o seu segredo do passo 1 |

Pode apagar `MAILJET_API_KEY`, `MAILJET_SECRET_KEY`, `BREVO_API_KEY` e `MAIL_FROM`, se existirem.
Salve: o Render publica o app de novo sozinho.

## 5. Teste

No site, use **Esqueci a senha** com uma conta criada com e-mail e senha (contas Google/Apple não recebem).
O e-mail chega como enviado pelo seu Gmail. Nos **Logs** do Render aparece:

- `[E-MAIL ENVIADO]` — deu certo.
- `[FALHA AO ENVIAR E-MAIL] ... Segredo incorreto` — o segredo do Render é diferente do script.
- `[FALHA AO ENVIAR E-MAIL] ... não respondeu como esperado` — a URL não termina em `/exec`
  ou a implantação não está com "Quem pode acessar: Qualquer pessoa".
- `[E-MAIL NÃO ENVIADO]` — as variáveis não chegaram no Render; confira os nomes.

## Mudou o script depois?

Salvar não basta: vá em **Implantar** → **Gerenciar implantações** → lápis (editar) →
em "Versão" escolha **Nova versão** → **Implantar**. A URL continua a mesma.
