"""Testes das ferramentas de catálogo — sem chamar LLM."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_loader import DataLoader
from tools.products import ProductTools

loader = DataLoader()
loader.load_all()
tools = ProductTools(loader)


def test_order_most_expensive_first():
    """'Mais caro' precisa vir do catálogo inteiro, não dos 10 primeiros por preço."""
    result = tools.search_products(category_name="Violões", order="maior_preco", limit=3)
    in_stock = loader.products[(loader.products.category_id == 5) & (loader.products.stock_quantity > 0)]
    assert result["produtos"][0]["price_brl"] == in_stock["price_brl"].max()
    assert result["total_encontrado"] == len(in_stock)
    print("✅ test_order_most_expensive_first: OK")


def test_order_cheapest_first_is_default():
    result = tools.search_products(category_name="Violões", limit=1)
    assert result["produtos"][0]["name"] == "Tagima Memphis AC-39 Nylon Natural"
    print("✅ test_order_cheapest_first_is_default: OK")


def test_search_status_cases():
    assert tools.search_products(category_name="Atabaques")["status"] == "nao_vendemos"
    assert tools.search_products(category_name="violino")["status"] == "categoria_sem_produtos"
    assert tools.search_products(category_name="Violões", price_max=100)["status"] == "nenhum_resultado"
    gf3d = tools.search_products(category_name="Violões", brand="Giannini", price_min=790, price_max=800)
    assert gf3d["status"] == "sem_estoque"
    print("✅ test_search_status_cases: OK")


def test_search_by_name_partial():
    assert tools.search_by_name("Takamine GD20")["produtos"][0]["product_id"] == 95
    assert tools.search_by_name("giannini gf3d")["produtos"][0]["product_id"] == 96
    print("✅ test_search_by_name_partial: OK")


if __name__ == "__main__":
    print("🧪 Executando testes de catálogo...\n")
    test_order_most_expensive_first()
    test_order_cheapest_first_is_default()
    test_search_status_cases()
    test_search_by_name_partial()
    print("\n✅ Todos os testes passaram!")
