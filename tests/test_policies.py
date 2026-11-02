"""Testes do manual e do horário de funcionamento (sem chamar o LLM)."""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.policies import CAMPO_GRANDE_TZ, load_manual_text, store_status


def at(day: str, hour: int, minute: int = 0) -> datetime:
    y, m, d = map(int, day.split("-"))
    return datetime(y, m, d, hour, minute, tzinfo=CAMPO_GRANDE_TZ)


def test_manual_contains_key_rules():
    text = load_manual_text()
    for fragment in ["Rua 14 de Maio, 3200", "7 (sete) dias corridos", "5% de desconto", "09:00 às 18:00"]:
        assert fragment in text, f"Trecho ausente no manual: {fragment}"


def test_weekday_open_and_closed():
    assert store_status(at("2026-11-04", 10))["loja_aberta_agora"] is True   # quarta 10h
    assert store_status(at("2026-11-04", 18))["loja_aberta_agora"] is False  # quarta 18h já fechou
    assert store_status(at("2026-11-04", 8, 59))["proxima_abertura"] == "hoje às 09:00"


def test_saturday_closes_at_13():
    assert store_status(at("2026-11-07", 12, 59))["loja_aberta_agora"] is True
    status = store_status(at("2026-11-07", 13))
    assert status["loja_aberta_agora"] is False
    assert status["proxima_abertura"] == "segunda-feira, 09/11 às 09:00"


def test_sunday_and_holiday_closed():
    sunday = store_status(at("2026-11-01", 11))
    assert sunday["loja_aberta_agora"] is False and sunday["horario_de_hoje"] == "fechado"
    finados = store_status(at("2026-11-02", 11))  # segunda-feira, feriado de Finados
    assert finados["loja_aberta_agora"] is False and finados["feriado"] == "Finados"
    assert finados["proxima_abertura"] == "terça-feira, 03/11 às 09:00"
