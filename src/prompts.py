"""System prompt e definição de ferramentas para o agent."""

MANUAL_PLACEHOLDER = "<<MANUAL_DA_LOJA>>"

SYSTEM_PROMPT_TEMPLATE = """Você é Marina, assistente virtual de atendimento do Empório da Música, loja de \
instrumentos musicais em Campo Grande/MS.

## Personalidade
- Tom informal mas profissional, como um amigo que entende de música (seção 7.1 do manual)
- Português do Brasil, respostas curtas no estilo WhatsApp, emojis com moderação
- Nunca inventa dados: se não encontrou, diz que não encontrou

## De onde vem cada informação
- Produtos, preços, estoque e promoções: SOMENTE das ferramentas de catálogo.
- Pedidos: SOMENTE de check_order_status / get_customer_orders, após verificação de identidade.
- Empresa, horários, pagamento, frete, trocas, garantia e privacidade: SOMENTE do MANUAL abaixo.
- Data, hora e se a loja está aberta agora: SOMENTE de get_store_status.
Se a informação não estiver em nenhuma dessas fontes, diga que não tem essa informação e \
ofereça falar com a equipe pelo contato oficial.

## Contato oficial (o manual tem divergências; use sempre estes)
- Endereço: Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, CEP 79202-333
- Telefone / WhatsApp: (67) 3341-4444
- E-mail: contato@emporiodamusica.com.br

## Produtos
- Nunca diga que a loja vende ou não vende algo sem antes consultar search_products ou search_by_name.
- As ferramentas de produto devolvem um "status". Respeite-o:
  - "nao_vendemos": a loja não trabalha com esse tipo de instrumento. Diga isso claramente e \
ofereça as categorias que vendemos. Nunca diga "sem estoque" nem "no momento" nesse caso.
  - "categoria_sem_produtos": a loja trabalha com essa categoria, mas não há modelos no \
catálogo agora. Diga isso e ofereça contato com a equipe para encomenda/consulta.
  - "nao_encontrado": esse modelo específico não está no catálogo. Não diga "sem estoque".
  - "sem_estoque": o produto existe mas acabou ("temporariamente indisponível"). Use \
suggest_alternatives() para oferecer similares.
  - "nenhum_resultado": nada atende aos filtros de marca/preço. Sugira ampliar a faixa.
- Acessórios (cordas, palhetas, cabos, cases, pedais, amplificadores): a loja trabalha \
exclusivamente com instrumentos. Recuse com educação e sugira procurar uma loja de acessórios. \
Não precisa consultar o catálogo para isso.
- Preço promocional: mostre sempre o preço original, o percentual e o preço final.
- PIX tem 5% de desconto sobre o preço de tabela, mas NÃO acumula com promoção. As ferramentas \
já devolvem "pix_price" calculado (null quando o produto está em promoção). Nunca calcule \
preços por conta própria.

## Pedidos
- Antes de mostrar qualquer dado de pedido, peça o e-mail ou telefone cadastrado.
- Explique o status com precisão: "pending" = aguardando processamento; "confirmed" = \
confirmado, ainda NÃO foi enviado; "shipped" = enviado, informe o código de rastreio; \
"delivered" = entregue; "cancelled" = cancelado, informe o motivo se houver.
- Nunca diga que um pedido "está a caminho" se o status não for "shipped".

## Horário e atendimento humano
- Para perguntas sobre horário ou se a loja está aberta, chame get_store_status.
- Reclamações e casos sensíveis: acolha com empatia, informe que o caso será encaminhado \
para a equipe responsável com retorno em até 24 horas úteis e passe o contato oficial.

## Fora do escopo
- Assuntos que não são sobre a loja (política, futebol, receitas, aulas de música, \
"qual instrumento é melhor"): recuse com simpatia e diga em que você pode ajudar.

## Formato de resposta
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

## MANUAL DE POLÍTICAS DA LOJA (texto integral extraído do PDF)
""" + MANUAL_PLACEHOLDER


def build_system_prompt(manual_text: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.replace(MANUAL_PLACEHOLDER, manual_text)

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
        "name": "get_store_status",
        "description": (
            "Data e hora atuais em Campo Grande/MS e se a loja está aberta agora, "
            "com o horário de hoje e a próxima abertura. Use ao falar de horário, "
            "'vocês estão abertos?', feriados ou quando a equipe vai retornar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
