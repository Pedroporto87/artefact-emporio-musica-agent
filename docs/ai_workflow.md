# Como usei IA neste projeto

Registro do trabalho com o Claude Code (extensão do VS Code), na ordem em que aconteceu. Antes de começar, usei o Claude no chat para entender o case e escrever o briefing do projeto: contexto, requisitos, direção técnica sugerida e checklist de entrega. O briefing também definia a forma de trabalhar: o assistente explora os dados e propõe um plano antes de escrever código, e eu aprovo as decisões.

O histórico do git mostra a mesma sequência (`git log --reverse`).

## 1. Exploração e plano (01/11)

| O que pedi | O que o assistente fez | O que eu decidi ou revisei |
|---|---|---|
| Explorar `data/` antes de qualquer código | Levantou o schema dos 6 CSVs (65 produtos, 50 clientes, 20 pedidos, 25 promoções) e propôs um plano com arquitetura, ferramentas, suposições e riscos | Aprovei function calling. Pedi verificação de identidade por e-mail ou telefone (os CSVs não têm CPF). Criei o repositório no GitHub |

## 2. Primeira versão, sem execução (01/11, 16:12 a 16:23)

O assistente escreveu loader, ferramentas, agente, CLI, exemplos e README em sete commits, num intervalo de 11 minutos. **Nada disso foi executado:** o Python da minha máquina estava corrompido, e o código foi escrito sem teste. O README daquele momento marcava o checklist como cumprido, e os cinco exemplos de conversa tinham sido escritos à mão. Os itens seguintes corrigem isso.

## 3. Fazer rodar de verdade (01/11)

| O que aconteceu | O que o assistente fez | O que eu decidi ou revisei |
|---|---|---|
| Eu não queria pagar a API da Anthropic só para o protótipo | Migrou para a API compatível com OpenAI, apontando para o OpenRouter | Indiquei a chave que eu já tinha num projeto pessoal. Reinstalei o Python |
| `pandas==2.1.3` não instalava no Python novo | Trocou as versões fixas por mínimas | Testei a instalação |
| O agente respondia "ocorreu um erro" a qualquer pergunta. Trocar o modelo no `.env` não mudava nada | Várias rodadas de debug me pedindo para testar. Só depois de eu dizer "estamos em looping no erro" ele revisou o código: o modelo estava fixo, as ferramentas estavam no formato da Anthropic e os resultados iam sem `tool_call_id` | Cobrei que ele mesmo testasse antes de me devolver. Desse ponto em diante, toda mudança passou a ser rodada com o LLM antes do commit |
| Os testes de telefone falhavam | Os testes nunca tinham rodado: esperavam 10 dígitos para um número de 11 | |

## 4. Comportamento do agente (01/11 e 02/11)

Cada linha começa com algo que eu vi ao usar o agente ou que apareceu nos testes.

| Problema | Causa | Correção |
|---|---|---|
| "Atabaques sem estoque no momento" para algo que a loja nunca vendeu | Lista vazia para dois casos diferentes | A busca devolve um `status` explícito. A regra veio de mim: se não está no banco, a loja não vende |
| Preço inventado (R$ 849,90 para um produto de R$ 849,00) e "não trabalhamos com baterias" | O modelo respondia sem consultar a ferramenta | Checagem no código antes de enviar a resposta |
| "Qual o endereço?" ficava sem resposta | A ferramenta de políticas devolvia 5 linhas soltas do PDF | Manual inteiro no prompt e ferramenta de horário. Eu aprovei não editar o PDF e documentar as divergências dele |
| "Qual seu violão mais caro?" respondia o mais barato | A busca ordenava sempre do mais barato e cortava em 10 itens | Parâmetro de ordenação na ferramenta |
| Card de produto que a Marina não tinha citado | O "3" de "Kit 3" casava com o preço "R$ 4.439,00" | Comparação por palavra inteira |
| Pedido entregue há 352 dias "ainda dentro do prazo de devolução" | O modelo não sabe a data de hoje nem conta dias | Os prazos do manual saem calculados da ferramenta de pedidos. Esse erro só apareceu ao gerar os exemplos reais |

## 5. Funcionalidades que eu pedi (02/11)

| O que pedi | O que o assistente fez | O que eu decidi ou revisei |
|---|---|---|
| Home page com o catálogo e a Marina conversando | FastAPI e uma página HTML/JS sem build. Testou pela API e por capturas de tela | Testei na minha máquina e reportei os bugs dos itens acima |
| Orçamento de frete do endereço da loja até o cliente | Pesquisou as opções e recomendou o Melhor Envio. Não aceitou deixar o LLM estimar o valor, porque o manual proíbe passar preço sem consultar o sistema | Criei a conta no sandbox e o token. A regra de Campo Grande e o frete especial para baterias vêm do manual |

## 6. Revisão final (02/11)

| O que pedi | O que o assistente fez |
|---|---|
| Revisar o README | Reescreveu do zero, porque o anterior tinha afirmações falsas (modelo errado, checklist não verificado) |
| Gerar os exemplos de verdade | Apagou os exemplos escritos à mão. Os novos saem de `examples/inputs/*.txt` pela CLI, sem edição |
| Tirar a aparência de código gerado | Removeu emojis dos prints, código morto e comentários que repetiam o código. Os commits deixaram de ter a linha de coautoria do assistente |

## O que aprendi sobre usar o assistente

- **Sem execução, o código só parece pronto.** A primeira versão estava bem organizada e não funcionava. O ganho real começou quando passei a exigir teste de ponta a ponta antes de cada commit.
- **O assistente precisa revisar o próprio trabalho.** Pedir explicitamente "o que está errado no que você fez" encontrou os exemplos escritos à mão e o README com afirmações falsas.
- **As decisões de negócio continuaram comigo:** o que conta como "não vendemos", não editar o PDF da loja, qual provedor usar e quando parar de adicionar funcionalidades.
