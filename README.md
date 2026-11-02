# Empório da Música: agente de atendimento

Protótipo de um agente de atendimento por mensagens para a **Empório da Música**, loja fictícia de instrumentos musicais em Campo Grande/MS. Case técnico para a vaga de AI Engineer da Artefact.

A **Marina**, assistente virtual da loja, responde sobre:

- **Catálogo**: produtos, preços, estoque, promoções vigentes e preço no PIX.
- **Pedidos**: status e rastreio, só depois de verificar a identidade do cliente.
- **Frete**: estimativa até o CEP do cliente, com a regra do manual em Campo Grande e cotação no Melhor Envio para outras cidades.
- **Políticas**: horário, pagamento, frete, trocas, garantia e privacidade, com base no manual da loja.
- **Fora do escopo**: recusa com simpatia e redireciona para o que a loja faz.

Há duas interfaces: uma **home page** com o catálogo e o chat da Marina, e uma **CLI**.

---

## Como rodar

**Requisitos:** Python 3.10 ou superior (desenvolvido e testado com Python 3.15 no Windows) e uma chave do [OpenRouter](https://openrouter.ai).

```bash
git clone https://github.com/Pedroporto87/artefact-emporio-musica-agent.git
cd artefact-emporio-musica-agent

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha a chave:

```env
LLM_API_KEY=sk-or-v1-...
LLM_MODEL=openai/gpt-4o-mini
LLM_BASE_URL=https://openrouter.ai/api/v1
MELHOR_ENVIO_TOKEN=          # opcional, ver abaixo
```

O `.env` está no `.gitignore` e nunca é versionado.

**Cotação de frete (opcional):** crie uma conta gratuita em https://sandbox.melhorenvio.com.br. Em **Integrações → Permissões de acesso**, gere um token com a permissão `shipping-calculate`. A consulta no sandbox não tem custo. Sem o token, o agente funciona normalmente e, para fora de Campo Grande, informa só as modalidades e os prazos do manual.

**Home page (catálogo + chat):**

```bash
python src/web.py
```

Acesse http://127.0.0.1:8000.

**CLI:**

```bash
python src/main.py
```

Digite `sair` para encerrar.

**Testes** (determinísticos, sem chamar o LLM):

```bash
pytest
```

---

## Arquitetura

```
Cliente ──► Home page (src/static)  ──► FastAPI (src/web.py) ─┐
        └─► CLI (src/main.py) ─────────────────────────────────┤
                                                               ▼
                                              MusicaAgent (src/agent.py)
                         system prompt = persona + regras + MANUAL DA LOJA (PDF inteiro)
                                                               │  function calling
               ┌───────────────────────────┬───────────────────┼─────────────────────┐
               ▼                           ▼                   ▼                     ▼
   ProductTools (catálogo)        OrderTools (pedidos)   get_store_status     Checagem de respostas
   busca, detalhes, promoções,    status com verificação  (data/hora e         (preço sem origem,
   alternativas, preço PIX        de identidade           loja aberta?)        negação sem consulta)
               └───────────────────────────┴──────────────┘
                                 DataLoader (CSVs limpos em pandas)
```

O LLM decide **o que** consultar e **como** falar. Tudo o que é dado (preço, estoque, status, horário, desconto) vem de código determinístico.

---

## Decisões técnicas

### 1. Function calling em vez de RAG puro ou agente SQL

**Decisão:** o LLM tem 9 ferramentas tipadas (busca de produtos, detalhes, promoções, alternativas, busca por nome, status do pedido, pedidos do cliente, estimativa de frete e status da loja) e escolhe quais chamar.

**Por quê:** as perguntas mais frequentes envolvem números que não podem estar errados. Com ferramentas, o preço vem da tabela, não da memória do modelo, e cada ferramenta pode ser testada sem LLM.

**Alternativas descartadas:**
- **RAG sobre os CSVs:** busca semântica não sabe fazer "preço até R$ 1.000" ou "em estoque". São filtros exatos.
- **Agente que gera SQL:** mais flexível, mas o modelo poderia montar consultas erradas ou ler a tabela de clientes sem verificação de identidade. Com ferramentas, a verificação fica no código.

### 2. Manual de políticas inteiro no prompt, sem RAG

**Decisão:** o PDF (8 páginas, cerca de 11 mil caracteres, uns 3 mil tokens) é extraído com `pdfplumber` e vai integralmente no system prompt.

**Por quê:** cabe com folga no contexto. Assim o modelo vê todas as regras e as exceções juntas. Por exemplo, o desconto de 5% no PIX (seção 3) não acumula com promoção (seção 6.2). Um RAG com top-k poderia trazer um trecho e esquecer o outro.

**Histórico:** a primeira versão buscava linhas do PDF por palavra-chave e devolvia no máximo 5 linhas. Nos testes, regras se perdiam, e "qual o endereço?" ficava sem resposta. A troca resolveu os dois problemas.

**Quando mudaria:** com um manual de dezenas de páginas, eu partiria para chunking por seção, embeddings e top-k.

### 3. Ferramentas devolvem um `status` explícito

**Decisão:** a busca de produtos não devolve só uma lista. Ela devolve `ok`, `sem_estoque`, `nao_vendemos`, `categoria_sem_produtos`, `nao_encontrado` ou `nenhum_resultado`.

**Por quê:** com lista vazia, o modelo não sabe se a loja não vende o item ou se ele acabou. Nos testes, o agente respondia "atabaques sem estoque no momento", sugerindo que voltariam, para algo que a loja nunca vendeu. Com o status, cada caso tem uma resposta certa:

| Situação | Exemplo | Resposta esperada |
|---|---|---|
| Não está no catálogo nem nas categorias | atabaque | "Não trabalhamos com atabaques" |
| Categoria da loja sem modelos cadastrados | violino (Cordas Orquestrais) | "Não há modelos no catálogo agora", com contato da equipe |
| Existe, mas sem estoque | Giannini GF-3D | "Temporariamente indisponível" e sugestões de alternativas |
| Acessório | cordas, pedais | "A loja trabalha só com instrumentos" (manual, seção 7.1) |

### 4. Checagem determinística da resposta antes de enviar

**Decisão:** antes de devolver a resposta, o agente confere dois pontos:
1. Todo valor em R$ citado precisa aparecer em um resultado de ferramenta, no manual ou na mensagem do cliente.
2. Se a resposta disser "não temos" ou "não trabalhamos", alguma ferramenta de catálogo precisa ter sido chamada naquele turno.

Se uma das regras falhar, o modelo recebe o problema e reescreve a resposta, uma única vez. A correção não aparece para o cliente.

**Por quê:** instrução no prompt reduz a invenção de dados, mas não elimina. Nos testes, essa checagem pegou casos reais: um preço inventado (R$ 849,90 para um produto de R$ 849,00) e "não trabalhamos com baterias", sendo que a loja vende três.

**Limite:** a checagem confere números e negações, não o raciocínio. Ver [Limitações](#limitações-conhecidas).

### 5. Contas e datas no código, não no LLM

- **Preço no PIX:** o código calcula 5% de desconto e devolve `null` quando o produto está em promoção, porque o manual diz que os descontos não acumulam.
- **Promoção vigente:** o preço final é calculado a partir do `discount_percent` da promoção com `is_active = 1`.
- **Mais caro e mais barato:** `search_products` recebe `order` (`maior_preco` ou `menor_preco`) e informa `total_encontrado`. Antes, a lista vinha sempre do mais barato para o mais caro e cortada em 10 itens. Ao ouvir "qual o violão mais caro?", a Marina escolhia dentro dos 10 mais baratos e respondia R$ 429,90, quando o mais caro custa R$ 12.000,00.
- **Loja aberta agora:** `get_store_status` usa o horário de Campo Grande (UTC-4, sem horário de verão desde 2019), o horário do manual e os feriados nacionais de data fixa. A resposta inclui a próxima abertura, por exemplo "terça-feira, 03/11 às 09:00".

**Por quê:** LLM erra aritmética e não sabe que dia é hoje.

### 6. Modelo e provedor: `openai/gpt-4o-mini` via OpenRouter

**Decisão:** API compatível com OpenAI apontando para o OpenRouter. O modelo é configurável no `.env`.

**Por quê:**
- O OpenRouter permite trocar de modelo sem mudar código, só com o `LLM_MODEL`.
- Eu já tinha uma chave do OpenRouter, o que evitou pagar outra API só para o protótipo.
- O `gpt-4o-mini` é barato, rápido e foi o modelo com que todo o comportamento foi validado: tool calling, português e persona.

**Histórico:** o plano inicial era Claude Haiku pela API da Anthropic. Ao migrar para o OpenRouter, o primeiro modelo testado (`google/gemini-3.6-flash`) retornava `MALFORMED_FUNCTION_CALL`. A causa era um bug meu: as ferramentas estavam no formato da API da Anthropic, e o modelo estava fixo no código, ignorando o `.env`. Depois da correção, validei o `gpt-4o-mini`. Os outros modelos não foram reavaliados.

### 7. Verificação de identidade para pedidos

**Decisão:** antes de mostrar um pedido, o agente pede e-mail ou telefone, e o código confere com o cadastro do cliente daquele pedido. O telefone é comparado só pelos dígitos, então "(67) 99654-7821" e "67996547821" são equivalentes.

**Por quê:** pedido tem dado pessoal, e o manual cita a LGPD (seção 9). A verificação está na ferramenta, não no prompt. Mesmo que o modelo tente, sem e-mail ou telefone corretos a ferramenta não devolve os dados.

**CPF:** o desafio sugere CPF como opção, mas `customers.csv` não tem essa coluna. Ficou só e-mail e telefone (ver [Suposições](#suposições)).

### 8. Tratamento de dados

O `DataLoader` carrega os 6 CSVs com `pandas` em memória (65 produtos, 50 clientes, 20 pedidos). Os tratamentos aplicados:

| Campo | Tratamento | Motivo |
|---|---|---|
| Tipos | `int`, `float`, `datetime` explícitos | Evitar comparações erradas entre texto e número |
| `specs` | JSON → `dict` | Ficha técnica (tampo, cordas, eletrônica) disponível para o agente |
| Nomes | Sem acento e em minúsculas (`name_normalized`) | Busca tolerante: "violao" encontra "Violão" |
| Busca por nome | `token_set_ratio` e hífens ignorados | "Takamine GD20" encontra "Takamine GD20 Dreadnought Natural", e "gf3d" encontra "GF-3D" |
| Categorias | Plural do português e limiar de 90% | Com limiar de 80%, "violinos" casava com "violões" |
| Telefone | Só dígitos | Verificação independente de formatação |

**Por que não um banco de dados:** com esse volume, `pandas` em memória responde em milissegundos e não exige setup. SQLite faria sentido com escrita (pedidos novos, histórico persistente). Ver [O que faria com mais tempo](#o-que-faria-com-mais-tempo).

### 9. Interfaces: home page em FastAPI + CLI

**Decisão:** FastAPI servindo uma página HTML/CSS/JS sem framework nem build, mais uma CLI.

**Por quê:**
- Tudo fica em Python no back-end, a única restrição do case.
- A página mostra o que um chat em texto não mostra: o catálogo por categoria e, quando a Marina cita produtos, cards clicáveis que destacam o item no catálogo.
- Sem build, é só rodar `python src/web.py`.
- A CLI continua útil para testar o agente sem navegador.

**Alternativas descartadas:** Streamlit e Gradio são mais rápidos para um chat simples, mas dão pouco controle sobre um layout de catálogo com chat lateral.

### 10. Histórico de conversa em memória, por sessão

**Decisão:** cada visitante da home page (ou execução da CLI) tem uma instância do agente com o histórico em memória. A página guarda o `session_id` no `sessionStorage`.

**Por quê:** o multi-turno é necessário (o agente pede o e-mail numa mensagem e consulta o pedido na seguinte), mas persistir conversas entre reinícios não traz ganho para um protótipo e criaria uma obrigação de LGPD.

### 11. Estimativa de frete: regra do manual + Melhor Envio

**Decisão:** a ferramenta `estimate_shipping(cep, product_id)` segue um caminho por tipo de destino:
1. O **ViaCEP** (gratuito, sem chave) valida o CEP e identifica a cidade.
2. **Campo Grande:** aplica a regra do manual (5.1) sem API: grátis acima de R$ 500, senão R$ 35, entrega por motoboy em 1 a 3 dias úteis.
3. **Baterias e teclados/pianos:** a Marina encaminha para cotação individual, como o manual exige para instrumentos de grande porte (5.2).
4. **Outras cidades:** cotação no **Melhor Envio**, com origem na loja (CEP 79202-333). A resposta mostra só os serviços disponíveis, ordenados por preço, e sempre como estimativa.
5. **Sem token ou com falha na API:** a Marina informa as modalidades e os prazos do manual, sem valor.

**Por quê:**
- O Melhor Envio cota numa única chamada as transportadoras que o manual cita (Correios e Jadlog).
- Tem sandbox gratuito, e a API oficial dos Correios exige contrato.
- O valor vem da API, não do LLM. Isso respeita a regra do manual de nunca passar preço ou prazo sem consultar o sistema (7.1).

**Alternativa descartada:** deixar o LLM estimar o frete. O valor mudaria a cada conversa e não teria base nenhuma.

**Observação dos testes:** para um violão (caixa de 110 cm), PAC e SEDEX são recusados por excederem o limite de dimensões dos Correios, e só a Jadlog cota. A ferramenta trata esse caso e mostra apenas o que está disponível.

### 12. Estratégia de prompt

O system prompt (`src/prompts.py`) tem, nesta ordem:
1. **Persona**, com o tom de voz do manual (seção 7.1): informal mas profissional.
2. **De onde vem cada informação**: catálogo só das ferramentas, políticas só do manual, horário só de `get_store_status`.
3. **Contato oficial**, porque o manual se contradiz (ver Suposições).
4. **Regras por assunto**: como interpretar cada `status`, acessórios, PIX, status de pedido, reclamações.
5. **Exemplos de formato**, sem produtos nem preços reais. Quando os exemplos tinham preços reais, o modelo os repetia sem consultar a ferramenta.
6. **O manual inteiro.**

---

## Suposições

O enunciado pede para assumir interpretações razoáveis e documentá-las.

| # | Ambiguidade | Suposição |
|---|---|---|
| 1 | O manual dá dois WhatsApp: (67) 3341-4444 na tabela de dados e (67) 3321-4500 na seção 7 | Usar **(67) 3341-4444**, que aparece duas vezes, inclusive na tabela oficial de dados da empresa |
| 2 | O e-mail aparece como `empóriodamusica` (com acento, inválido) | Usar `contato@emporiodamusica.com.br` |
| 3 | O manual diz que a loja vende sopros e cordas orquestrais, mas os CSVs não têm nenhum produto dessas categorias | A loja trabalha com essas categorias, mas não há modelos no catálogo agora. O agente diz isso e oferece contato com a equipe |
| 4 | `promotions.csv` não tem datas de início e fim | `is_active = 1` significa vigente hoje |
| 5 | `customers.csv` não tem CPF | Verificação por e-mail ou telefone |
| 6 | O manual fala em feriados, sem listar quais | Feriados nacionais de data fixa. Os móveis (Carnaval, Sexta-feira Santa, Corpus Christi) não estão incluídos |
| 7 | Os pedidos vão de 2025 a 2026 | São tratados como dados reais da loja, com o status que está no CSV |
| 8 | Os CSVs não têm peso nem dimensões dos produtos, que a cotação de frete exige | Embalagem estimada por categoria em `src/tools/shipping.py`. Exemplo: violão com 2,5 kg em caixa de 110×45×15 cm. O seguro usa o preço de venda, com promoção aplicada |
| 9 | O manual fala em "região metropolitana de Campo Grande" sem listar as cidades | Só a cidade de Campo Grande recebe a regra de entrega local. As demais são cotadas pelo Melhor Envio |
| 10 | "Fora do escopo" | Tudo que não é catálogo, pedido ou política da loja: futebol, aulas de música, "qual instrumento é melhor" etc. |

---

## Limitações conhecidas

- **Erros de raciocínio do modelo não são detectados.** A checagem confere números e negações, não a lógica da resposta. O caso mais visível ("qual o violão mais caro?" respondido com o mais barato) foi resolvido no código: ver a decisão 5.
- **Respostas variam entre execuções.** O mesmo pedido pode gerar listas diferentes ou chamadas de ferramentas desnecessárias (por exemplo, consultar o horário numa pergunta sobre frete).
- **A checagem corrige uma vez só.** Se o modelo errar de novo na reescrita, a resposta sai assim.
- **O frete é uma estimativa.** Usa dimensões estimadas por categoria e o sandbox do Melhor Envio, cujos preços podem diferir da produção.
- **Sem persistência:** o histórico se perde quando o servidor reinicia.
- **Sem autenticação nem rate limit na API web.** Adequado para rodar localmente, não para expor publicamente.
- **O loop do agente não tem testes automatizados.** Os testes cobrem ferramentas e regras; o comportamento do agente com o LLM foi validado com cenários executados manualmente.

## O que faria com mais tempo

1. **Avaliação automatizada:** um conjunto de 30 a 50 perguntas com respostas esperadas (preço correto, recusa correta, verificação exigida), rodado a cada mudança de prompt ou de modelo, para comparar modelos com números.
2. **SQLite** como fonte dos dados, quando houver escrita (novos pedidos, reclamações registradas) e histórico persistente com política de retenção.
3. **Encaminhamento real para humano:** hoje a Marina informa o prazo de 24h úteis, mas não cria um registro.
4. **Integração com WhatsApp**, o canal citado no manual.
5. **Frete em produção:** peso e dimensões reais de cada produto e o token de produção do Melhor Envio.

---

## Testes

`pytest` roda 24 testes, nenhum chama o LLM ou a internet:

| Arquivo | Testes | O que cobre |
|---|---|---|
| `tests/test_data_loader.py` | 11 | Carga, tipos, normalização, verificação de identidade, promoção, PIX |
| `tests/test_policies.py` | 4 | Manual extraído, horário em dia útil, sábado, domingo e Finados |
| `tests/test_products.py` | 4 | Ordenação por preço, status da busca, busca por nome parcial |
| `tests/test_shipping.py` | 5 | CEP inválido, regra de Campo Grande, frete especial, cotação (APIs simuladas) |

---

## Estrutura

```
├── data/                     # CSVs e manual em PDF fornecidos (não alterados)
├── src/
│   ├── web.py                # FastAPI: home page, /api/catalog, /api/chat
│   ├── static/               # index.html, style.css, app.js
│   ├── main.py               # CLI
│   ├── agent.py              # loop de function calling + checagem das respostas
│   ├── prompts.py            # persona, regras e definição das ferramentas
│   ├── data_loader.py        # carga e limpeza dos CSVs
│   └── tools/
│       ├── products.py       # catálogo, promoções, alternativas, status de busca
│       ├── orders.py         # pedidos com verificação de identidade
│       ├── shipping.py       # estimativa de frete (manual + ViaCEP + Melhor Envio)
│       └── policies.py       # leitura do manual e horário de funcionamento
├── tests/
├── examples/
└── docs/ai_workflow.md       # registro do uso de IA etapa por etapa
```

---

## Uso de assistentes de código

Usei o **Claude** em dois papéis:
- **Claude (chat):** entender o case e montar o briefing do projeto (`CLAUDE.md`), com contexto, requisitos, direção técnica sugerida e um checklist de entrega.
- **Claude Code (extensão do VS Code):** explorar os dados, propor o plano, implementar, testar e fazer os commits.

**Como foi o workflow:**
1. **Briefing primeiro.** O `CLAUDE.md` define que o assistente explora os dados e propõe um plano antes de escrever código, e que eu aprovo cada decisão. Eu escolhi a arquitetura (function calling), o provedor (OpenRouter, para não pagar outra API) e as regras de negócio. Um exemplo: "se não está no banco, a loja não vende".
2. **Commits pequenos.** Cada passo lógico vira um commit, como o processo pede.
3. **Testar de verdade mudou o resultado.** A primeira versão foi escrita sem ser executada. Quando rodei na minha máquina, nada funcionava: o modelo estava fixo no código, as ferramentas estavam no formato errado para a API e os testes de telefone esperavam o número de dígitos errado. A partir daí, passei a exigir que cada mudança fosse testada de ponta a ponta com o LLM antes do commit. Foi nesses testes que apareceram o "sem estoque" para atabaque, o preço inventado e a negação de produtos que a loja vende. As soluções estão nas decisões 3 e 4.
4. **Revisão crítica.** Pedi ao assistente que apontasse o que estava errado no próprio trabalho. Isso levou a reescrever este README, que antes afirmava coisas não verificadas, e a refazer os exemplos de conversa, que tinham sido escritos à mão.

O registro etapa por etapa (o que pedi, o que o assistente fez, o que revisei) está em [docs/ai_workflow.md](docs/ai_workflow.md).
