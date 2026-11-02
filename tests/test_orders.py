"""Testes de pedidos: verificação de identidade e prazos do manual (sem chamar o LLM)."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_loader import DataLoader
from tools.orders import OrderTools, deadlines_after_delivery

loader = DataLoader()
loader.load_all()
orders = OrderTools(loader)


def test_order_needs_matching_email_or_phone():
    assert orders.check_order_status(2)["status"] == "verificacao_necessaria"
    assert orders.check_order_status(2, "lucas.mendes@jmail.com")["status"] == "verificacao_falhou"
    assert orders.check_order_status(2, "Thiago.Barbosa@jmail.com")["status"] == "ok"
    assert orders.check_order_status(8, "67996547821")["status"] == "ok"


def test_unknown_order():
    assert orders.check_order_status(999, "thiago.barbosa@jmail.com")["status"] == "pedido_nao_encontrado"


def test_deadlines_counted_from_delivery():
    delivered = date(2026, 3, 1)
    assert deadlines_after_delivery(delivered, date(2026, 3, 8))["arrependimento_7_dias"] == "dentro do prazo"
    later = deadlines_after_delivery(delivered, date(2026, 3, 9))
    assert later["arrependimento_7_dias"] == "prazo encerrado"
    assert later["troca_por_defeito_30_dias"] == "dentro do prazo"
    assert deadlines_after_delivery(delivered, date(2026, 6, 1))["garantia_legal_90_dias"] == "prazo encerrado"


def test_delivered_order_includes_deadlines():
    result = orders.check_order_status(2, "thiago.barbosa@jmail.com")
    assert result["order_status"] == "delivered"
    assert result["prazos_pos_entrega"]["data_de_entrega_considerada"] == "2025-11-15"
    assert "prazos_pos_entrega" not in orders.check_order_status(8, "67996547821")  # enviado, ainda não entregue
