# Cenários de exemplo no formato documental da skill cenarios-de-teste.
CONTEXTO
DADO que há um cadastro ativo com o e-mail "qa@exemplo.com"
E não está logado na plataforma

CT001 - Envio do link de recuperação para e-mail cadastrado
DADO que está na tela "Esqueci minha senha"
QUANDO é informado o e-mail "qa@exemplo.com"
E é acionado "Enviar link"
ENTÃO é exibida a mensagem "Se o e-mail estiver cadastrado, você receberá um link"
E chega um e-mail com o link de redefinição

CT002 - Mesma mensagem para e-mail não cadastrado
DADO que está na tela "Esqueci minha senha"
QUANDO é informado o e-mail "nao.existe@exemplo.com"
E é acionado "Enviar link"
ENTÃO é exibida a mensagem "Se o e-mail estiver cadastrado, você receberá um link"
E nenhum e-mail é enviado

CT003 - Link de redefinição expirado
DADO que há um link de redefinição gerado há mais de 24 horas
QUANDO o link é aberto
ENTÃO é exibida a mensagem de link expirado
E é oferecida a opção de gerar um novo link
