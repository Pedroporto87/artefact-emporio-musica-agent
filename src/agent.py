"""Agent loop com function calling via API compatível com OpenAI (OpenRouter)."""

import json
import os
import re
from typing import Any, Dict, List
from openai import OpenAI
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data_loader import DataLoader
from tools.products import ProductTools
from tools.orders import OrderTools
from tools.policies import load_manual_text, store_status
from prompts import build_system_prompt, TOOLS_DEFINITION

DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOOL_ROUNDS = 5

BRL_PRICE_RE = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)")
PLAIN_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
DENIAL_RE = re.compile(r"n[ãa]o (trabalhamos|vendemos|temos|possu[ií]mos)", re.IGNORECASE)
PRODUCT_TOOLS = {"search_products", "search_by_name", "get_product_details", "suggest_alternatives"}
# Seção 7.1 do manual: acessórios não são vendidos, então negar não exige consultar o catálogo.
ACCESSORY_RE = re.compile(r"corda|palheta|cabo|case|pedal|pedais|amplificador|acess[óo]rio", re.IGNORECASE)


def _brl_to_float(text: str) -> float:
    return round(float(text.replace(".", "").replace(",", ".")), 2)

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
    def __init__(self, api_key: str, model: str = None, base_url: str = None, verbose: bool = False,
                 loader: DataLoader = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL,
        )
        self.model = model or os.getenv("LLM_MODEL") or DEFAULT_MODEL
        self.verbose = verbose

        if loader is None:
            loader = DataLoader()
            loader.load_all()
        self.loader = loader

        self.product_tools = ProductTools(self.loader)
        self.order_tools = OrderTools(self.loader)
        self.system_prompt = build_system_prompt(load_manual_text())

        self.conversation_history: List[Dict[str, Any]] = []
        # IDs de produtos devolvidos pelas ferramentas no último turno (a home page mostra os cards).
        self.last_product_ids: List[int] = []

    def process_message(self, user_message: str) -> str:
        """Processa uma mensagem do cliente e retorna a resposta do agente."""
        self.conversation_history.append({"role": "user", "content": user_message})
        self.last_product_ids = []
        # Mensagens de correção da checagem de preços: vão para o modelo, mas não ficam no histórico.
        correction: List[Dict[str, Any]] = []
        product_tool_called = False

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
                messages=[{"role": "system", "content": self.system_prompt}, *self.conversation_history, *correction],
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
                    product_tool_called |= tc.function.name in PRODUCT_TOOLS
                    self._collect_product_ids(result)
                    if self.verbose:
                        print(f"  [tool] {tc.function.name}({args})")
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })
                continue

            if choice.finish_reason in ("stop", "length") and message.content:
                problem = self._grounding_problem(message.content, product_tool_called)
                if problem and not correction:
                    if self.verbose:
                        print(f"  [checagem] {problem}")
                    correction = [
                        {"role": "assistant", "content": message.content},
                        {"role": "user", "content": (
                            f"[verificação automática do sistema, não é o cliente] {problem} "
                            "Consulte a ferramenta adequada antes de responder ao cliente. Responda direto "
                            "ao cliente, sem mencionar esta verificação nem pedir desculpas por ela."
                        )},
                    ]
                    continue
                self.conversation_history.append({"role": "assistant", "content": message.content})
                return message.content

            raise RuntimeError(
                f"Resposta inesperada do modelo {response.model}: finish_reason={choice.finish_reason}"
            )

        return "Desculpe, não consegui concluir sua solicitação agora. Pode reformular a pergunta? 😕"

    def _collect_product_ids(self, obj: Any) -> None:
        if isinstance(obj, dict):
            pid = obj.get("product_id")
            if isinstance(pid, int) and pid not in self.last_product_ids:
                self.last_product_ids.append(pid)
            for value in obj.values():
                self._collect_product_ids(value)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_product_ids(item)

    def _grounding_problem(self, text: str, product_tool_called: bool) -> str:
        """Descreve por que a resposta não está apoiada em dados, ou "" se estiver ok."""
        ungrounded = self._ungrounded_prices(text)
        if ungrounded:
            return f"Sua resposta cita valores que não vieram de nenhuma ferramenta: {ungrounded}."
        if DENIAL_RE.search(text) and not product_tool_called and not ACCESSORY_RE.search(text):
            return "Sua resposta afirma que a loja não vende/não tem algo sem ter consultado o catálogo."
        return ""

    def _ungrounded_prices(self, text: str) -> List[str]:
        """Valores em R$ da resposta que não aparecem no manual, nas ferramentas nem nas falas do cliente."""
        known = {_brl_to_float(p) for p in BRL_PRICE_RE.findall(self.system_prompt)}
        for msg in self.conversation_history:
            content = msg.get("content")
            if not isinstance(content, str):
                continue
            if msg["role"] == "tool":
                known.update(round(float(n), 2) for n in PLAIN_NUMBER_RE.findall(content))
            elif msg["role"] == "user":
                known.update(_brl_to_float(p) for p in BRL_PRICE_RE.findall(content))
                known.update(float(n) for n in re.findall(r"\d+", content))
        return [f"R$ {p}" for p in BRL_PRICE_RE.findall(text) if _brl_to_float(p) not in known]

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
                    order=tool_input.get("order", "menor_preco"),
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
            if tool_name == "get_store_status":
                return store_status()
            return {"error": f"Ferramenta desconhecida: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}

    def reset_conversation(self):
        self.conversation_history = []
