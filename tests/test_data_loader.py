"""Testes para data_loader.py — sem chamar LLM."""

import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_loader import DataLoader


def test_load_all():
    """Testa carregamento de todos os CSVs."""
    loader = DataLoader()
    loader.load_all()

    assert loader.products is not None
    assert loader.categories is not None
    assert loader.customers is not None
    assert loader.orders is not None
    assert loader.order_items is not None
    assert loader.promotions is not None

    print("✅ test_load_all: OK")


def test_products_schema():
    """Verifica schema do products."""
    loader = DataLoader()
    loader.load_all()

    required_cols = ["product_id", "price_brl", "name", "category_id", "stock_quantity"]
    for col in required_cols:
        assert col in loader.products.columns, f"Coluna {col} não encontrada"

    # Checar tipos
    assert loader.products["product_id"].dtype == "int64"
    assert loader.products["price_brl"].dtype == "float64"
    assert loader.products["stock_quantity"].dtype == "int64"

    print("✅ test_products_schema: OK")


def test_normalize_text():
    """Testa normalização de texto (remoção de acentos)."""
    assert DataLoader._normalize_text("Violão") == "violao"
    assert DataLoader._normalize_text("AÇÚCAR") == "acucar"
    assert DataLoader._normalize_text("São Paulo") == "sao paulo"
    assert DataLoader._normalize_text("Yamaha C70") == "yamaha c70"

    print("✅ test_normalize_text: OK")


def test_normalize_phone():
    """Testa normalização de telefone."""
    assert DataLoader._normalize_phone("(67) 99812-3456") == "67998123456"
    assert DataLoader._normalize_phone("67 99812-3456") == "67998123456"
    assert DataLoader._normalize_phone("67998123456") == "67998123456"

    print("✅ test_normalize_phone: OK")


def test_parse_specs():
    """Testa parsing de JSON specs."""
    specs_json = '{"top":"Spruce","back_sides":"Meranti","neck":"Nato"}'
    result = DataLoader._parse_specs(specs_json)
    assert isinstance(result, dict)
    assert result.get("top") == "Spruce"

    # Teste com specs com barras duplas escapadas
    specs_escaped = '{"top":"Spruce Sólido","back_sides":"Nato"}'
    result2 = DataLoader._parse_specs(specs_escaped)
    assert isinstance(result2, dict)

    print("✅ test_parse_specs: OK")


def test_get_category_name():
    """Testa busca de nome de categoria."""
    loader = DataLoader()
    loader.load_all()

    # Categoria 5 deve ser "Violões"
    cat_name = loader.get_category_name(5)
    assert cat_name == "Violões", f"Esperado 'Violões', obtido '{cat_name}'"

    # Categoria inexistente
    cat_none = loader.get_category_name(999)
    assert cat_none is None

    print("✅ test_get_category_name: OK")


def test_verify_customer_email():
    """Testa verificação de cliente por email."""
    loader = DataLoader()
    loader.load_all()

    # Cliente 1: Lucas Mendes (email: lucas.mendes@jmail.com)
    verified = loader.verify_customer(1, email="lucas.mendes@jmail.com")
    assert verified is True, "Cliente 1 deveria ser verificado por email"

    # Email errado
    verified_wrong = loader.verify_customer(1, email="wrong@email.com")
    assert verified_wrong is False, "Email errado deveria falhar"

    print("✅ test_verify_customer_email: OK")


def test_verify_customer_phone():
    """Testa verificação de cliente por phone."""
    loader = DataLoader()
    loader.load_all()

    # Cliente 1: Lucas Mendes (phone: (67) 99812-3456)
    verified = loader.verify_customer(1, phone="(67) 99812-3456")
    assert verified is True, "Cliente 1 deveria ser verificado por phone"

    # Phone sem formatação
    verified2 = loader.verify_customer(1, phone="67998123456")
    assert verified2 is True, "Phone normalizado deveria funcionar"

    # Phone errado
    verified_wrong = loader.verify_customer(1, phone="(67) 99999-9999")
    assert verified_wrong is False, "Phone errado deveria falhar"

    print("✅ test_verify_customer_phone: OK")


def test_get_product_with_promotion():
    """Testa busca de produto com promoção ativa."""
    loader = DataLoader()
    loader.load_all()

    # Produto 95 tem uma promoção ativa
    prod = loader.get_product_with_promotion(95)
    assert prod is not None
    assert prod["product_id"] == 95
    assert "price_brl" in prod
    assert "promotion" in prod

    # Se tem promoção ativa, deve ter desconto
    if prod["promotion"] is not None:
        assert "discount_percent" in prod["promotion"]
        assert "discounted_price" in prod["promotion"]

    print("✅ test_get_product_with_promotion: OK")


def test_nonexistent_product():
    """Testa busca de produto inexistente."""
    loader = DataLoader()
    loader.load_all()

    prod = loader.get_product_with_promotion(99999)
    assert prod is None

    print("✅ test_nonexistent_product: OK")


if __name__ == "__main__":
    print("🧪 Executando testes de data_loader...\n")

    test_load_all()
    test_products_schema()
    test_normalize_text()
    test_normalize_phone()
    test_parse_specs()
    test_get_category_name()
    test_verify_customer_email()
    test_verify_customer_phone()
    test_get_product_with_promotion()
    test_nonexistent_product()

    print("\n✅ Todos os testes passaram!")
