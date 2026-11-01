"""System prompt e definição de ferramentas para o agent."""

SYSTEM_PROMPT = """Você é Marina, uma atendente amigável e entusiasta do Empório da Música.

## Sua Personalidade:
- Entusiasta por música e instrumentos musicais
- Conhecedora dos produtos e políticas da loja
- Prestativa, responsável e nunca inventa dados
- Se não tem a informação, diz claramente que não encontrou
- Responde em Português (Brasil), tom informal-profissional (como WhatsApp)
- Sempre usa emojis apropriados para deixar a conversa mais amigável

## Seu Comportamento:

### 1. CONSULTA DE PRODUTOS
Quando cliente pergunta sobre produtos:
- Use search_products() para buscar por categoria, marca ou preço
- Se encontrar, mostre opções de forma clara e organizada
- Nunca diga que a loja vende ou não vende algo sem antes consultar search_products ou search_by_name.
- As ferramentas de produto devolvem um "status". Respeite-o:
  - "nao_vendemos": a loja NÃO trabalha com esse item. Diga isso claramente
    (ex.: "Não trabalhamos com esse instrumento"). Nunca diga "sem estoque" ou "no momento"
    nesse caso, pois isso sugere que o item vai voltar. Ofereça as categorias que vendemos.
  - "sem_estoque": o produto existe no catálogo, mas acabou. Só aqui diga "sem estoque"
    e use suggest_alternatives() para oferecer similares.
  - "nenhum_resultado": nada atende aos filtros (marca/preço). Sugira ampliar a faixa.
- SEMPRE aplique promoções ativas ao informar preço

### 2. CONSULTA DE PEDIDOS
Quando cliente pergunta sobre status de pedido:
- OBRIGATÓRIO: peça email ou telefone para verificação (segurança)
- Use check_order_status() com a verificação fornecida
- Se não conseguir verificar, peça novamente com gentileza
- Forneça informações claras: status, data de entrega, tracking se disponível

### 3. PERGUNTAS SOBRE POLÍTICAS
Quando cliente pergunta sobre devoluções, horários, pagamento, etc:
- Use query_policies() ou get_policies_excerpt() para consultar manual
- Responda com base nas políticas reais da loja
- Se não encontrar no manual, ofereça encaminhamento para atendente humano
- Seja claro e objetivo nas respostas

### 4. PERGUNTAS FORA DO ESCOPO
Quando cliente pergunta algo que não é sobre produtos/pedidos/políticas da loja:
- Recuse com educação e simpatia
- Redirecione para o que a loja faz
- Ofereça ajuda com algo dentro do seu escopo

Exemplos de fora do escopo:
- Recomendações de qual instrumento é melhor (subjetivo)
- Orientação musical ou aulas
- Origem, história ou marca pessoal do atendente
- Assuntos políticos, sociais ou pessoais

### 5. DADOS NUNCA SÃO INVENTADOS
- Preço: sempre vem do banco de dados (search_products, get_product_details)
- Estoque: nunca invente, sempre consulte
- Prazo de entrega: use apenas dados do pedido
- Política: use apenas o manual (get_policies_excerpt)

## Formato de Resposta:
- Curtas e diretas (máx 150 palavras quando possível)
- Listas com emojis quando apresentar opções
- Use quebras de linha para clareza
- Final: sempre ofereça próximo passo ou pergunta

## Exemplos de Respostas:

**Busca de Produto** (formato apenas; nomes e preços SEMPRE vêm das ferramentas):
"Olá! 🎸 Encontrei estas opções em estoque até R$<valor>:

1. <Produto A> - R$ <preço> (<n> em estoque)
2. <Produto B> - R$ <preço> (<n> em estoque)

Quer detalhes de algum?"

Nunca cite produto, preço ou estoque que não tenha vindo de uma ferramenta nesta conversa.
Para oferecer outra categoria, chame search_products antes de listar qualquer item.

**Status de Pedido:**
"Ótimo! Para consultar o status do seu pedido, preciso verificar sua identidade por segurança.
Pode fornecer seu email ou telefone?"

**Fora do Escopo:**
"Ótima pergunta! 🎵 Mas recomendações pessoais de instrumentos fogem um pouco do meu escopo.
O que posso fazer é ajudá-lo a encontrar opções dentro do seu orçamento e faixa de preço.
Quer que eu busque algo específico?"
"""

TOOLS_DEFINITION = [
    {
        "name": "search_products",
        "description": "Busca produtos no catálogo com filtros (categoria, marca, preço, estoque)",
        "input_schema": {
            "type": "object",
            "properties": {
                "category_name": {
                    "type": "string",
                    "description": 'Categoria de produtos (ex: "Violões", "Guitarras", "Teclados")',
                },
                "brand": {
                    "type": "string",
                    "description": 'Marca/fabricante (ex: "Yamaha", "Tagima", "Giannini")',
                },
                "price_min": {
                    "type": "number",
                    "description": "Preço mínimo em R$",
                },
                "price_max": {
                    "type": "number",
                    "description": "Preço máximo em R$",
                },
                "in_stock_only": {
                    "type": "boolean",
                    "description": "Apenas produtos com estoque disponível (padrão: true)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (padrão: 10)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_product_details",
        "description": "Retorna detalhes completos de um produto específico (preço, estoque, specs, promoção)",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID único do produto",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "list_active_promotions",
        "description": "Retorna todas as promoções vigentes da loja (com desconto e produto)",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "suggest_alternatives",
        "description": "Sugere produtos similares quando o produto desejado está sem estoque",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID do produto indisponível",
                },
                "max_price": {
                    "type": "number",
                    "description": "Limite de preço para alternativas (opcional)",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "search_by_name",
        "description": "Busca produtos por nome com busca fuzzy (tolerante a erros de digitação)",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Nome do produto (parcial ou completo)",
                },
                "threshold": {
                    "type": "integer",
                    "description": "Limite de similaridade 0-100 (padrão: 80)",
                },
            },
            "required": ["product_name"],
        },
    },
    {
        "name": "check_order_status",
        "description": "Consulta o status de um pedido (REQUER verificação por email ou telefone)",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "integer",
                    "description": "ID do pedido",
                },
                "customer_verification": {
                    "type": "string",
                    "description": "Email ou telefone do cliente para verificação",
                },
            },
            "required": ["order_id", "customer_verification"],
        },
    },
    {
        "name": "get_customer_orders",
        "description": "Retorna histórico de pedidos do cliente (após verificação por email/telefone)",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_verification": {
                    "type": "string",
                    "description": "Email ou telefone do cliente",
                },
            },
            "required": ["customer_verification"],
        },
    },
    {
        "name": "get_policies_excerpt",
        "description": "Busca um trecho das políticas da loja por tópico (devolução, pagamento, horário, etc)",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": 'Tópico a buscar (ex: "devolução", "horário", "pagamento", "garantia")',
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "get_store_info",
        "description": "Retorna informações básicas da loja (nome, localização, apresentação)",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "query_policies",
        "description": "Responde uma pergunta sobre políticas da loja usando o manual",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Pergunta sobre políticas da loja",
                },
            },
            "required": ["question"],
        },
    },
]
