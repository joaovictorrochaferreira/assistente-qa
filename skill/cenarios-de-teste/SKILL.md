---
name: cenarios-de-teste
description: >-
  Gera cenários de teste (CTs) em Gherkin (DADO/QUANDO/ENTÃO), em português, a
  partir de tarefa do ClickUp, diff de código no git e regras de negócio. Use
  sempre que o usuário pedir cenários de teste, casos de teste, CTs, testes em
  Gherkin, ou testes a partir de uma tarefa do ClickUp ou de um diff, mesmo
  sem dizer a palavra "skill". Conduz um fluxo de 7 etapas com confirmação do
  usuário entre cada uma (exceto a Etapa 6, automática): clarificação,
  Background, plano de testes, cenários fora da caixa, escrita iterativa,
  validação pelo conselho de QA (skill conselho-qa) e execução assistida sob
  demanda.
---

# Gerador de Cenários de Teste (CTs)

## Quando usar esta skill e visão geral do fluxo

Gera cenários de teste (CTs) em formato Gherkin (DADO/QUANDO/ENTÃO), em
português, a partir de uma tarefa do ClickUp, de alterações de código no git
(diff de branch ou de commits) e de regras de negócio.

Use sempre que o usuário pedir para criar cenários de teste, casos de teste,
CTs, testes em Gherkin, ou pedir para gerar testes a partir de uma tarefa do
ClickUp ou de um diff de código, mesmo que ele não diga a palavra "skill".

O fluxo é conduzido em etapas, com confirmação do usuário entre cada uma:

1. Análise e perguntas de clarificação
2. Definição do Background (contexto compartilhado)
3. Plano de testes (títulos)
4. Cenários adicionais "fora da caixa"
5. Escrita iterativa dos cenários
6. Validação automática dos cenários escritos pelo conselho de QA (skill `conselho-qa`)
7. Execução assistida dos cenários já escritos, sob demanda do usuário (ex.: "vamos executar", "me ajuda a validar o CTXXX")

NÃO avance de etapa sem confirmação. A Etapa 6 é a única exceção: dispara
automaticamente ao fim da Etapa 5.

Cria cenários de teste em Gherkin a partir das informações de uma tarefa. A
lógica central do fluxo é alinhar o entendimento **antes** de escrever dezenas
de cenários, para não gastar esforço em cima de premissas erradas.

## Fontes de informação (entradas)

Use **apenas as fontes que o usuário fornecer**; nenhuma é obrigatória
isoladamente. Mas você precisa de contexto suficiente para gerar bons cenários:
se não houver nem tarefa, nem regras de negócio, nem código, pergunte antes de
prosseguir.

### Tarefa do ClickUp (via MCP)
Quando o usuário fornecer um link ou ID de tarefa (ex.:
`https://app.clickup.com/t/123456/ABC-123`, ID `ABC-123`):
- Leia a **descrição da tarefa** com `clickup_get_task` (aceita IDs customizados
  como `ABC-123`; passe `include: ["description"]` para trazer o texto completo,
  pois por padrão vem truncado).
- Leia os **comentários** com `clickup_get_task_comments`. Se algum comentário
  tiver `reply_count > 0`, busque as respostas com `clickup_get_threaded_comments`.
- O usuário costuma indicar o comentário relevante por data/hora (ex.:
  "comentário de 17/06 às 6:10 pm"). Localize esse comentário e trate o conteúdo
  dele como parte do contexto.
- Se o comentário indicado não for encontrado, avise e liste os comentários
  disponíveis para o usuário confirmar qual é.
- **O MCP do ClickUp é somente leitura.** A skill não cria nem preenche tarefas:
  quem insere os cenários no ClickUp é o usuário (copiando e colando a saída no
  modelo dele). Por isso, priorize gerar a saída já no formato pronto para colar.

### Alterações de código (git)
Se você tiver acesso ao repositório local, há duas formas de obter o diff;
prefira a primeira.

**1. Diff da branch da tarefa contra a branch base (recomendado).**
Mostra tudo o que a branch introduziu e fica sempre atualizado conforme novos
commits chegam.
- Descubra a branch da tarefa. Se ela já estiver em checkout no repositório,
  detecte com `git rev-parse --abbrev-ref HEAD`. Caso contrário, peça o nome ao
  usuário.
- Atualize as referências antes de comparar: `git fetch`.
- Gere o diff com **três pontos**, contra a base (ex.: `main` ou `develop`):
  ```
  git diff <base>...<branch-da-tarefa>
  ```
  Os três pontos (`...`) mostram exatamente o que a branch adicionou desde que
  saiu da base, a mesma visão de um Pull Request. Se não souber qual é a base,
  pergunte.

**2. Diff entre dois commits específicos (quando o usuário fornecer os hashes).**
```
git diff <hashA>..<hashB>
```
Use quando o usuário quiser fixar um intervalo exato de commits (dois pontos).

**Fallback (sem acesso ao repositório).** Se os comandos `git` não estiverem
disponíveis no ambiente (por exemplo, sem o repositório montado), não insista
neles: peça ao usuário para **colar o diff** e trate o texto colado como a fonte
de código.

Analise o diff para entender o comportamento **realmente implementado**, não só
o que está descrito na tarefa.

### Regras de negócio / observações do usuário
Considere qualquer contexto adicional colado pelo usuário: restrições do sistema,
perfis de usuário envolvidos, regras de negócio e adendos/comentários dele. Dê
peso especial a esses adendos, pois costumam carregar a intenção real do teste.

## Fluxo de trabalho (em ordem, com confirmação entre etapas)

Não avance para a próxima etapa sem a confirmação do usuário. As etapas existem
para alinhar o entendimento antes da escrita em massa.

### Etapa 1: Análise e perguntas de clarificação
Cruze as fontes fornecidas (tarefa, código, regras de negócio) e aponte:
- Pontos ambíguos, incompletos ou contraditórios na descrição da tarefa.
- Comportamentos presentes no código que não estão documentados na tarefa.
- Conflitos entre o que foi descrito e o que foi implementado.

Faça as perguntas necessárias para alinhar esses pontos. **Não sugira cenários
ainda.**

### Etapa 2: Background (Contexto)
Logo após a clarificação, defina o **Background**: os passos de pré-condição
comuns a todos os cenários (o DADO compartilhado que se repetiria em cada um).
Proponha esse Background ao usuário e **confirme explicitamente que o contexto do
teste foi compreendido antes de continuar**. Não avance sem essa confirmação.

Se a tarefa envolver **mais de um Background** (por exemplo, grupos de cenários
com pré-condições distintas: perfis, estados iniciais ou fluxos diferentes),
**não escolha sozinho**: aponte isso ao usuário e pergunte como ele quer tratar
(quantos Backgrounds haverá e quais cenários pertencem a cada um). Se um contexto
distinto só ficar evidente ao montar o plano (Etapa 3), levante a questão ali.

### Etapa 3: Proposta do plano de testes
Com o contexto confirmado, proponha uma lista de **títulos** de cenários,
organizados por grupos (ex.: Fluxo Principal, Validações, Permissões,
Regressão). Essa lista serve de índice para os cenários e para o usuário depois
inseri-los no modelo dele no ClickUp. **Não escreva o detalhe de nenhum cenário
ainda.**

### Etapa 4: Cenários "fora da caixa" (opcional, recomendado)
Sugira cenários adicionais aplicando **técnicas de qualidade, mas só as que
fizerem sentido para a tarefa em questão**. Não despeje uma checklist fixa:
escolha as lentes pertinentes ao que está sendo testado e justifique
brevemente por que cada uma cabe ali. Lentes possíveis:

- **Valores de fronteira / partição de equivalência**: quando houver entradas
  numéricas, datas, limites de tamanho ou faixas.
- **Permissões e perfis**: quando houver papéis, níveis de acesso ou visões
  distintas por usuário.
- **Concorrência / simultaneidade**: quando houver processamento paralelo,
  filas, ações simultâneas ou estado compartilhado.
- **Integração com outras funcionalidades**: quando a mudança afetar ou
  depender de outros fluxos do sistema.
- **Segurança**: quando houver dados sensíveis, autenticação ou validação de
  permissão no back-end.
- **Casos de borda do diff**: comportamentos, condições ou tratamentos de erro
  que aparecem no código mas não estão descritos na tarefa.

Se uma lente não se aplica à tarefa (ex.: não há entrada numérica, então não force
"valores de fronteira"), simplesmente não a proponha. Deixe o usuário decidir
quais cenários entram na lista definitiva.

### Etapa 5: Escrita iterativa dos cenários
Após a lista final aprovada e o Background confirmado, escreva **um cenário por
vez**. Aguarde o comando "próximo" para escrever o seguinte.

### Etapa 6: Validação pelo conselho de QA (automática)
Assim que o **último** cenário da lista aprovada (Etapa 5) for escrito, dispare
a skill `conselho-qa` para validar o conjunto completo, **sem pedir
confirmação antes de disparar**. Essa é a única etapa automática do fluxo.

Entregue ao conselho o pacote de revisão:
- o Background confirmado e todos os cenários escritos, no texto final;
- as fontes usadas (tarefa, diff, regras de negócio e observações do usuário);
- as decisões alinhadas nas Etapas 1 e 2 e os cenários que o usuário recusou
  na Etapa 4, para que não sejam sugeridos de novo;
- a seção "Formato de saída (obrigatório)" desta skill, como regra de formato.

Apresente o parecer do conselho ao usuário **antes de aplicar qualquer
mudança**. O conselho só dá parecer, e quem decide aplicar ou não é o usuário.
Se algum ajuste for aprovado, atualize os cenários afetados e mostre a versão
final antes de seguir para a Etapa 7.

**Se a skill `conselho-qa` não estiver disponível**, faça você mesmo uma
revisão com os mesmos quatro critérios (cobertura, técnicas de teste, execução
manual e regra de negócio) e a checagem de formato. Exija evidência para cada
apontamento, aceite "sem apontamentos" como resultado válido e avise o usuário
que foi uma revisão simplificada, sem revisores independentes.

### Etapa 7: Execução assistida (opcional, sob demanda)
Essa etapa **só começa se o usuário pedir explicitamente**, depois que os
cenários já estiverem escritos (ex.: "vamos executar", "me ajuda a validar
isso", "o que eu faço no CT005", "explica esse cenário"). Não entre nela
automaticamente ao terminar a Etapa 6.

O objetivo é ajudar o usuário a **rodar os cenários no ambiente real dele**,
não relê-los. Isso normalmente envolve investigar a implementação real (diff,
classes, queries, schema de banco) para embasar a orientação em comportamento
implementado de fato, não em suposição sobre o que "deveria" acontecer.

- **Traduza DADO/QUANDO/ENTÃO em ações concretas** no ambiente do usuário:
  quais dados/contas/telas usar, que ação tomar, e o que observar como
  resultado. Não repita o Gherkin de volta: o usuário já tem o cenário
  escrito; o valor aqui é o "como fazer isso na prática".
- **Se houver acesso (read-only) a banco de dados ou outra ferramenta de
  inspeção** (ex.: uma skill de conexão SQL), use-a para: estabelecer o
  estado "antes" de uma ação (baseline), prever o resultado esperado a partir
  da lógica real do código, e confirmar o resultado "depois", comparando com
  o que o cenário exige. Isso vale muito mais do que confiar só no que a tela
  mostra, especialmente quando o comportamento depende de dados sem
  visualização própria (contadores internos, timestamps, campos de estado).
- **Quando o resultado real não bater com o esperado, investigue a causa**
  (schema real vs. suposto, lógica do código, timing entre ações, dados de
  teste desatualizados) antes de concluir se é bug do sistema, cenário mal
  desenhado, ferramenta de apoio desatualizada, ou engano de leitura, nessa
  ordem de suspeita, não assumindo bug de cara.
- **Cenários difíceis ou impossíveis de reproduzir manualmente** (condições
  de corrida, estados que exigem manipulação de dado fora do alcance normal
  do usuário, timing muito curto) devem ser sinalizados como tal, com uma
  alternativa prática (nota para a dev, script de apoio, validação por
  leitura de código) em vez de insistir numa reprodução manual inviável, no
  mesmo padrão de honestidade da Etapa 4.
- **Mantenha o placar**: quais cenários já foram confirmados, quais estão
  pendentes, quais foram bloqueados/adiados. Informe quando o usuário
  perguntar o status geral.
- **Achados durante a execução podem gerar cenários novos** (bugs reais,
  lacunas de regra, comportamento não documentado descoberto na prática),
  proponha antes de escrever, do mesmo jeito que a Etapa 4.
- Se alguma ferramenta de apoio construída durante essa etapa (ex.: uma query
  de diagnóstico) ficar desatualizada por uma mudança no código, avise e
  atualize antes de o usuário confiar de novo nela.

## Formato de saída (obrigatório)

Estes cenários são **documentais**: escritos no estilo Gherkin para leitura e
execução manual por QA, e para colar no modelo de tarefa do ClickUp. **Não é
Gherkin executável**. O formato adotado aqui (palavras-chave em MAIÚSCULAS,
título `CT001 - ...` em vez de `Cenário:`, sem indentação) prioriza legibilidade
humana e não roda em ferramentas como o Cucumber sem adaptação. Mantenha o
formato abaixo mesmo que ele difira do Gherkin executável.

- **Formato:** Gherkin (DADO / QUANDO / ENTÃO).
- **Idioma:** totalmente em português.
- **Título:** ID sequencial (CT001, CT002, ...) + título descritivo conforme a
  lista aprovada.
- **Palavras-chave em MAIÚSCULAS:** DADO, QUANDO, ENTÃO e E. Use **E** (nunca
  "AND") para encadear passos.
- **Indentação:** nenhuma, sem espaços ou tabs no início das linhas.
- **Quebra de linha:** um passo por linha, com uma quebra simples ao final de
  cada linha. **Não** deixe linha em branco entre os passos.
- **Background:** exiba o Background confirmado uma única vez, antes dos
  cenários, em seu próprio bloco de código `text`, iniciado pela palavra
  CONTEXTO. Se houver mais de um Background, identifique cada um claramente.
- **Exibição:** apresente cada cenário criado dentro de um bloco de código do
  tipo `text`.
- **Objetividade (sem "encheção de linguiça"):** cada passo traz apenas estado
  (DADO), ação (QUANDO) ou resultado observável (ENTÃO). Não escreva linhas que
  expliquem o comportamento interno em vez de descrever um resultado verificável.
  Ex. a **evitar:** "E o processamento de uma conversa não bloqueia nem atrasa o
  processamento da outra": isso é justificativa, não um resultado testável.
- **Passos impessoais (não identificar o executor):** não nomeie quem/o que
  executa a ação ("E o QA acessa...", "o sistema exibe...", "o usuário
  clica..."). Reformule em terceira pessoa impessoal: "E acessa...", "ENTÃO é
  exibida...".
- **Sem nomes de ferramenta/produto interno:** descreva pela função, não pelo
  nome do produto. Ex.: "logado na plataforma" em vez de "logado e disponível no
  Sistema X"; "para o agente na tela de atendimento via chat" em vez de "Sistema
  X Chat".

**Exemplo completo (Background + cenários montados na sequência de entrega):**
```text
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
```

**Par "Evitar / Usar" (aplicando os anti-padrões):**

Este par corrige dois problemas de uma vez (nomear o executor e escrever
justificativa em vez de resultado verificável):
```
Evitar:  E o QA verifica que o sistema não trava com muitos registros
Usar:    ENTÃO a listagem é exibida sem travamento
```
```
Evitar:  E o processamento de uma conversa não bloqueia a outra
Usar:    ENTÃO as duas conversas são exibidas como processadas
```
