# Cenários de exemplo no formato documental da skill cenarios-de-teste.
CONTEXTO
DADO que está logado na plataforma
E com o perfil "Administrador"

CT001 - Login com credenciais válidas
DADO que está na tela de login
E há um cadastro ativo
QUANDO são informados e-mail e senha corretos
E é acionado "Entrar"
ENTÃO é feito o redirecionamento para a tela inicial
E é exibida a mensagem de boas-vindas

CT002 - Login com senha incorreta
DADO que está na tela de login
QUANDO é informada uma senha inválida
E é acionado "Entrar"
ENTÃO é exibida a mensagem de erro
E permanece na tela de login
