"""Consulta de pedidos. Nenhum dado sai sem conferir e-mail ou telefone do cliente."""

from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd

from data_loader import DataLoader
from tools.policies import CAMPO_GRANDE_TZ

# Manual 4.1, 4.2 e 8.1, contados a partir do recebimento.
DEADLINES_AFTER_DELIVERY = {
    "arrependimento_7_dias": 7,
    "troca_por_defeito_30_dias": 30,
    "garantia_legal_90_dias": 90,
}

STATUS_DESCRIPTIONS = {
    "pending": "Pedido recebido, aguardando processamento.",
    "confirmed": "Pedido confirmado, ainda não foi enviado.",
    "shipped": "Pedido enviado, a caminho do cliente.",
    "delivered": "Pedido entregue.",
    "cancelled": "Pedido cancelado.",
}


def _date(value) -> Optional[str]:
    return str(value.date()) if pd.notna(value) else None


def _text(value) -> Optional[str]:
    return value if pd.notna(value) else None


def deadlines_after_delivery(delivered_on: date, today: Optional[date] = None) -> Dict:
    """O modelo não sabe a data de hoje nem conta dias: o prazo de devolução sai calculado daqui."""
    today = today or datetime.now(CAMPO_GRANDE_TZ).date()
    days = (today - delivered_on).days
    return {
        "data_de_entrega_considerada": str(delivered_on),
        "hoje": str(today),
        "dias_desde_a_entrega": days,
        **{name: ("dentro do prazo" if days <= limit else "prazo encerrado")
           for name, limit in DEADLINES_AFTER_DELIVERY.items()},
        "observacao": "Fora da garantia legal, a garantia do fabricante (6 meses a 2 anos) pode valer; "
                      "a loja pode intermediar (manual 4.2 e 8.2).",
    }


class OrderTools:
    def __init__(self, loader: DataLoader):
        self.loader = loader

    def check_order_status(self, order_id: int, customer_verification: Optional[str] = None) -> Dict:
        orders = self.loader.orders
        match = orders[orders["order_id"] == order_id]
        if match.empty:
            return {"status": "pedido_nao_encontrado",
                    "mensagem": f"Não existe pedido número {order_id}. Peça ao cliente para conferir o número."}
        order = match.iloc[0]

        if not customer_verification:
            return {"status": "verificacao_necessaria",
                    "mensagem": "Peça o e-mail ou telefone cadastrado antes de mostrar o pedido."}
        if not self._verify(int(order["customer_id"]), customer_verification):
            # Mesma resposta para "não confere" e "pedido de outra pessoa": não revela de quem é o pedido.
            return {"status": "verificacao_falhou",
                    "mensagem": "E-mail ou telefone não conferem com o pedido. Peça para o cliente conferir."}

        items = self.loader.order_items[self.loader.order_items["order_id"] == order_id]
        result = {
            "status": "ok",
            "order_id": int(order["order_id"]),
            "order_status": order["status"],
            "status_description": STATUS_DESCRIPTIONS.get(order["status"], order["status"]),
            "order_date": _date(order["order_date"]),
            "total_brl": round(float(order["total_brl"]), 2),
            "payment_method": order["payment_method"],
            "items": int(items["quantity"].sum()),
            "tracking_code": _text(order["tracking_code"]),
            "estimated_delivery": _date(order["estimated_delivery"]),
            "notes": _text(order["notes"]),
        }
        # O CSV não tem a data real de entrega; para pedidos entregues, vale a data estimada.
        if order["status"] == "delivered" and pd.notna(order["estimated_delivery"]):
            result["prazos_pos_entrega"] = deadlines_after_delivery(order["estimated_delivery"].date())
        return result

    def get_customer_orders(self, customer_verification: str) -> List[Dict]:
        customer_id = self._find_customer(customer_verification)
        if customer_id is None:
            return []
        orders = self.loader.orders[self.loader.orders["customer_id"] == customer_id]
        summary = [
            {
                "order_id": int(row["order_id"]),
                "order_date": _date(row["order_date"]),
                "order_status": row["status"],
                "status_description": STATUS_DESCRIPTIONS.get(row["status"], row["status"]),
                "total_brl": round(float(row["total_brl"]), 2),
            }
            for _, row in orders.iterrows()
        ]
        return sorted(summary, key=lambda o: o["order_date"] or "", reverse=True)

    def _verify(self, customer_id: int, verification: str) -> bool:
        if "@" in verification:
            return self.loader.verify_customer(customer_id, email=verification)
        return self.loader.verify_customer(customer_id, phone=verification)

    def _find_customer(self, verification: str) -> Optional[int]:
        customers = self.loader.customers
        if "@" in verification:
            match = customers[customers["email"].str.lower() == verification.strip().lower()]
        else:
            match = customers[customers["phone_normalized"] == self.loader._normalize_phone(verification)]
        return None if match.empty else int(match.iloc[0]["customer_id"])
