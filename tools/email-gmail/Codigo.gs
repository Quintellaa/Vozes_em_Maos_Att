/**
 * Vozes em Mãos — envio de e-mail pelo Gmail (Google Apps Script)
 *
 * Este script roda nos servidores do Google, na sua conta. O backend do app manda
 * para ele "envie este e-mail para fulano", e ele envia pelo seu Gmail.
 * Serve para contornar o bloqueio de SMTP do plano grátis do Render.
 *
 * Passo a passo completo: COMO-CONFIGURAR-EMAIL.md (na raiz do projeto).
 *
 * Limite do Gmail comum: cerca de 100 e-mails por dia.
 */

// Troque pelo MESMO valor que você colocar em GMAIL_SCRIPT_SECRET no Render.
// Sem ele, qualquer pessoa que descobrisse o endereço do script poderia mandar e-mails pela sua conta.
const SEGREDO = 'TROQUE-POR-UMA-SENHA-LONGA';

const NOME_REMETENTE = 'Vozes em Mãos';


/** Chamado pelo backend do app (POST com JSON). */
function doPost(e) {
  let dados;
  try {
    dados = JSON.parse(e.postData.contents);
  } catch (err) {
    return responder({ ok: false, error: 'O pedido não veio em JSON.' });
  }

  if (SEGREDO === 'TROQUE-POR-UMA-SENHA-LONGA') {
    return responder({ ok: false, error: 'Troque o SEGREDO no topo do script e implante de novo.' });
  }
  if (!dados || dados.secret !== SEGREDO) {
    return responder({ ok: false, error: 'Segredo incorreto: GMAIL_SCRIPT_SECRET no Render é diferente do SEGREDO do script.' });
  }
  if (!dados.to || !dados.subject) {
    return responder({ ok: false, error: 'Faltou o destinatário ou o assunto.' });
  }

  try {
    MailApp.sendEmail({
      to: dados.to,
      subject: dados.subject,
      body: dados.text || '',
      htmlBody: dados.html || undefined,
      name: dados.name || NOME_REMETENTE,
    });
    return responder({ ok: true, restantesHoje: MailApp.getRemainingDailyQuota() });
  } catch (err) {
    return responder({ ok: false, error: String(err) });
  }
}


/** Abrir o endereço do script no navegador mostra isto — serve para conferir se está no ar. */
function doGet() {
  return responder({ ok: true, mensagem: 'Script de e-mail do Vozes em Mãos no ar.', restantesHoje: MailApp.getRemainingDailyQuota() });
}


/**
 * Rode esta função uma vez pelo botão "Executar" do editor:
 * o Google pede a autorização para o script enviar e-mails, e chega um e-mail de teste para você.
 */
function testarEnvio() {
  const eu = Session.getActiveUser().getEmail();
  MailApp.sendEmail(eu, 'Teste do Vozes em Mãos', 'Funcionou! O script consegue enviar e-mails pelo seu Gmail.');
  Logger.log('E-mail de teste enviado para ' + eu + '. Restam hoje: ' + MailApp.getRemainingDailyQuota());
}


function responder(objeto) {
  return ContentService.createTextOutput(JSON.stringify(objeto)).setMimeType(ContentService.MimeType.JSON);
}
