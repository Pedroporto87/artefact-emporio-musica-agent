"""Agent loop com function calling via API compatível com OpenAI (OpenRouter)."""

import json
import os
from typing import Any, Dict, List
from openai import OpenAI
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_loader import DataLoader
from tools.products import ProductTools
from tools.orders import OrderTools
from tools.policies import PolicyTools
from prompts import SYSTEM_PROMPT, TOOLS_DEFINITION

DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOOL_ROUNDS = 5

# prompts.py descreve as ferramentas com JSON Schema; aqui elas viram o formato OpenAI.
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in TOOLS_DEFINITION
]


class MusicaAgent:
    def __init__(self, api_key: str, model: str = None, base_url: str = None, verbose: bool = False):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL,
        )
        self.model = model or os.getenv("LLM_MODEL") or DEFAULT_MODEL
        self.verbose = verbose

        self.loader = DataLoader()
        self.loader.load_all()

        self.product_tools = ProductTools(self.loader)
        self.order_tools = OrderTools(self.loader)
        self.policy_tools = PolicyTools()

        self.conversation_history: List[Dict[str, Any]] = []

    def process_message(self, user_message: str) -> str:
        """Processa uma mensagem do cliente e retorna a resposta do agente."""
        self.conversation_history.append({"role": "user", "content": user_message})

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, *self.conversation_history],
            )
            choice = response.choices[0]
            message = choice.message

            if message.tool_calls:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in message.tool_calls
                    ],
                })
                for tc in message.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = self._execute_tool(tc.function.name, args)
                    if self.verbose:
                        print(f"  [tool] {tc.function.name}({args})")
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })
                continue

            if choice.finish_reason in ("stop", "length") and message.content:
                self.conversation_history.append({"role": "assistant", "content": message.content})
                return message.content

            raise RuntimeError(
                f"Resposta inesperada do modelo {response.model}: finish_reason={choice.finish_reason}"
            )

        return "Desculpe, não consegui concluir sua solicitação agora. Pode reformular a pergunta? 😕"

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Executa uma ferramenta e retorna o resultado."""
        try:
            if tool_name == "search_products":
                return self.product_tools.search_products(
                    category_name=tool_input.get("category_name"),
                    brand=tool_input.get("brand"),
                    price_min=tool_input.get("price_min"),
                    price_max=tool_input.get("price_max"),
                    in_stock_only=tool_input.get("in_stock_only", True),
                    limit=tool_input.get("limit", 10),
                )
            if tool_name == "get_product_details":
                result = self.product_tools.get_product_details(tool_input.get("product_id"))
                return result if result else {"error": "Produto não encontrado"}
            if tool_name == "list_active_promotions":
                return self.product_tools.list_active_promotions()
            if tool_name == "suggest_alternatives":
                return self.product_tools.suggest_alternatives(
                    product_id=tool_input.get("product_id"),
                    max_price=tool_input.get("max_price"),
                )
            if tool_name == "search_by_name":
                return self.product_tools.search_by_name(
                    product_name=tool_input.get("product_name"),
                    threshold=tool_input.get("threshold", 60),
                )
            if tool_name == "check_order_status":
                return self.order_tools.check_order_status(
                    order_id=tool_input.get("order_id"),
                    customer_verification=tool_input.get("customer_verification"),
                )
            if tool_name == "get_customer_orders":
                return self.order_tools.get_customer_orders(
                    customer_verification=tool_input.get("customer_verification"),
                )
            if tool_name == "get_policies_excerpt":
                return self.policy_tools.get_policies_excerpt(topic=tool_input.get("topic"))
            if tool_name == "get_store_info":
                return self.policy_tools.get_store_info()
            if tool_name == "query_policies":
                return self.policy_tools.query_policies(question=tool_input.get("question"))
            return {"error": f"Ferramenta desconhecida: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}

    def reset_conversation(self):
        self.conversation_history = []
