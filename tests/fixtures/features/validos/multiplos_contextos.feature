CONTEXTO - Administrador
DADO que está logado na plataforma
E com o perfil "Administrador"

CONTEXTO - Operador
DADO que está logado na plataforma
E com o perfil "Operador"

CT001 - Administrador acessa a tela de configurações
DADO que está na tela inicial
QUANDO é acionado o menu "Configurações"
ENTÃO é exibida a tela de configurações

CT002 - Operador não vê o menu de configurações
DADO que está na tela inicial
QUANDO o menu lateral é aberto
ENTÃO o item "Configurações" não é exibido
