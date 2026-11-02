"""Testes da estimativa de frete — ViaCEP e Melhor Envio simulados, sem rede."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tools.shipping as shipping

VIOLAO = {"category_id": 5, "sale_price": 2199.0}
UKULELE = {"category_id": 9, "sale_price": 159.9}
BATERIA = {"category_id": 3, "sale_price": 4439.0}

CITIES = {"79002000": {"cidade": "Campo Grande", "uf": "MS", "bairro": "Centro"},
          "01310100": {"cidade": "São Paulo", "uf": "SP", "bairro": "Bela Vista"}}
shipping.lookup_cep = lambda cep: CITIES.get(cep)
shipping.quote_melhor_envio = lambda cep, package, value, qty, token: [
    {"transportadora": "Jadlog", "servico": ".Package", "preco": 156.48, "prazo_dias_uteis": 5}]


def test_invalid_and_unknown_cep():
    assert shipping.estimate_shipping("123", VIOLAO)["status"] == "cep_invalido"
    assert shipping.estimate_shipping("99999-999", VIOLAO)["status"] == "cep_nao_encontrado"
    print("✅ test_invalid_and_unknown_cep: OK")


def test_campo_grande_rule_from_manual():
    above = shipping.estimate_shipping("79002-000", VIOLAO)
    assert above["opcoes"][0]["preco"] == 0.0 and above["opcoes"][0]["prazo"] == "1 a 3 dias úteis"
    below = shipping.estimate_shipping("79002000", UKULELE)
    assert below["opcoes"][0]["preco"] == 35.0
    print("✅ test_campo_grande_rule_from_manual: OK")


def test_large_instruments_need_special_quote():
    assert shipping.estimate_shipping("01310-100", BATERIA)["status"] == "frete_especial"
    print("✅ test_large_instruments_need_special_quote: OK")


def test_other_city_with_and_without_token():
    os.environ.pop("MELHOR_ENVIO_TOKEN", None)
    assert shipping.estimate_shipping("01310100", VIOLAO)["status"] == "sem_cotacao"
    os.environ["MELHOR_ENVIO_TOKEN"] = "teste"
    result = shipping.estimate_shipping("01310100", VIOLAO)
    assert result["status"] == "ok" and result["opcoes"][0]["preco"] == 156.48
    os.environ.pop("MELHOR_ENVIO_TOKEN")
    print("✅ test_other_city_with_and_without_token: OK")


def test_parse_quote_drops_refused_services():
    raw = [
        {"name": "PAC", "company": {"name": "Correios"}, "error": "Dimensões do objeto ultrapassam o limite"},
        {"name": ".Com", "company": {"name": "Jadlog"}, "custom_price": "176.24", "custom_delivery_time": 4},
        {"name": ".Package", "company": {"name": "Jadlog"}, "custom_price": "156.48", "custom_delivery_time": 5},
    ]
    parsed = shipping.parse_quote(raw)
    assert [o["servico"] for o in parsed] == [".Package", ".Com"]
    assert parsed[0]["preco"] == 156.48
    print("✅ test_parse_quote_drops_refused_services: OK")


if __name__ == "__main__":
    print("🧪 Executando testes de frete...\n")
    test_invalid_and_unknown_cep()
    test_campo_grande_rule_from_manual()
    test_large_instruments_need_special_quote()
    test_other_city_with_and_without_token()
    test_parse_quote_drops_refused_services()
    print("\n✅ Todos os testes passaram!")
