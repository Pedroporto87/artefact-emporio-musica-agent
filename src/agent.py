"""Agent loop com ReAct e function calling via OpenRouter."""

import json
from typing import Any, Optional, Dict, List
from openai import OpenAI
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_loader import DataLoader
from tools.products import ProductTools
from tools.orders import OrderTools
from tools.policies import PolicyTools
from prompts import SYSTEM_PROMPT, TOOLS_DEFINITION


class MusicaAgent:
    def __init__(self, api_key: str):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self.model = "google/gemini-3.6-flash"

        # Inicializar dados
        self.loader = DataLoader()
        self.loader.load_all()

        # Inicializar ferramentas
        self.product_tools = ProductTools(self.loader)
        self.order_tools = OrderTools(self.loader)
        self.policy_tools = PolicyTools()

        # Histórico da conversa
        self.conversation_history = []

    def process_message(self, user_message: str) -> str:
        """
        Processa uma mensagem do usuário e retorna resposta do agente.

        Args:
            user_message: Mensagem do cliente

        Returns:
            Resposta do agente em português
        """
        # Adicionar mensagem do usuário ao histórico
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        # Loop ReAct
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Chamar LLM via OpenRouter com as ferramentas
            # OpenRouter espera system como primeira mensagem, não como parâmetro
            messages_with_system = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *self.conversation_history,
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                tools=TOOLS_DEFINITION,
                tool_choice="auto",
                messages=messages_with_system,
            )

            # Processar resposta
            choice = response.choices[0]

            if choice.finish_reason == "tool_calls":
                # LLM quer usar uma ferramenta
                message = choice.message
                tool_results = []

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_input = json.loads(tool_call.function.arguments)
                    tool_use_id = tool_call.id

                    # Executar ferramenta
                    result = self._execute_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_call_id": tool_use_id,
                        "content": json.dumps(result, ensure_ascii=False, indent=2),
                    })

                # Adicionar resposta do LLM ao histórico
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                })

                # Adicionar resultados das ferramentas
                self.conversation_history.append({
                    "role": "tool",
                    "content": json.dumps(tool_results, ensure_ascii=False),
                })

            elif choice.finish_reason == "stop":
                # LLM finalizou com resposta texto
                final_response = choice.message.content or ""

                # Adicionar resposta final ao histórico
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_response,
                })

                return final_response

            else:
                # Outro finish_reason (improvável)
                return "Desculpe, ocorreu um erro ao processar sua mensagem. 😕"

        return "Desculpe, não consegui processar sua solicitação após várias tentativas. 😕"

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

            elif tool_name == "get_product_details":
                product_id = tool_input.get("product_id")
                result = self.product_tools.get_product_details(product_id)
                return result if result else {"error": "Produto não encontrado"}

            elif tool_name == "list_active_promotions":
                return self.product_tools.list_active_promotions()

            elif tool_name == "suggest_alternatives":
                return self.product_tools.suggest_alternatives(
                    product_id=tool_input.get("product_id"),
                    max_price=tool_input.get("max_price"),
                )

            elif tool_name == "search_by_name":
                return self.product_tools.search_by_name(
                    product_name=tool_input.get("product_name"),
                    threshold=tool_input.get("threshold", 80),
                )

            elif tool_name == "check_order_status":
                return self.order_tools.check_order_status(
                    order_id=tool_input.get("order_id"),
                    customer_verification=tool_input.get("customer_verification"),
                )

            elif tool_name == "get_customer_orders":
                return self.order_tools.get_customer_orders(
                    customer_verification=tool_input.get("customer_verification"),
                )

            elif tool_name == "get_policies_excerpt":
                return self.policy_tools.get_policies_excerpt(
                    topic=tool_input.get("topic"),
                )

            elif tool_name == "get_store_info":
                return self.policy_tools.get_store_info()

            elif tool_name == "query_policies":
                return self.policy_tools.query_policies(
                    question=tool_input.get("question"),
                )

            else:
                return {"error": f"Ferramenta desconhecida: {tool_name}"}

        except Exception as e:
            return {"error": str(e)}

    def reset_conversation(self):
        """Reseta o histórico da conversa."""
        self.conversation_history = []

    def get_conversation_history(self) -> List[Dict]:
        """Retorna o histórico da conversa."""
        return self.conversation_history
