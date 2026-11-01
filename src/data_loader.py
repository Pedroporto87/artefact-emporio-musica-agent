"""Carregamento e limpeza de dados dos CSVs."""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
import unicodedata


class DataLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.products = None
        self.categories = None
        self.customers = None
        self.orders = None
        self.order_items = None
        self.promotions = None

    def load_all(self):
        """Carrega todos os CSVs."""
        self.products = self._load_products()
        self.categories = self._load_categories()
        self.customers = self._load_customers()
        self.orders = self._load_orders()
        self.order_items = self._load_order_items()
        self.promotions = self._load_promotions()
        print("✅ Todos os dados carregados com sucesso.")

    def _load_products(self) -> pd.DataFrame:
        """Carrega products.csv com limpeza e normalização."""
        csv_file = self.data_dir / "desafio_tecnico_ai_eng - products.csv"
        df = pd.read_csv(csv_file, encoding="utf-8")

        # Normalizar tipos
        df["product_id"] = df["product_id"].astype(int)
        df["price_brl"] = pd.to_numeric(df["price_brl"], errors="coerce")
        df["category_id"] = df["category_id"].astype(int)
        df["stock_quantity"] = df["stock_quantity"].astype(int)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

        # Parsear JSON specs
        df["specs"] = df["specs"].apply(self._parse_specs)

        # Normalizar nomes para busca fuzzy
        df["name_normalized"] = df["name"].apply(self._normalize_text)

        # Remover nulos desnecessários
        df = df.fillna({
            "status": "active",
            "description": ""
        })

        return df

    def _load_categories(self) -> pd.DataFrame:
        """Carrega categories.csv."""
        csv_file = self.data_dir / "desafio_tecnico_ai_eng - categories.csv"
        df = pd.read_csv(csv_file, encoding="utf-8")
        df["category_id"] = df["category_id"].astype(int)
        return df

    def _load_customers(self) -> pd.DataFrame:
        """Carrega customers.csv."""
        csv_file = self.data_dir / "desafio_tecnico_ai_eng - customers.csv"
        df = pd.read_csv(csv_file, encoding="utf-8")
        df["customer_id"] = df["customer_id"].astype(int)
        # Normalizar phone para busca
        df["phone_normalized"] = df["phone"].apply(self._normalize_phone)
        return df

    def _load_orders(self) -> pd.DataFrame:
        """Carrega orders.csv."""
        csv_file = self.data_dir / "desafio_tecnico_ai_eng - orders.csv"
        df = pd.read_csv(csv_file, encoding="utf-8")
        df["order_id"] = df["order_id"].astype(int)
        df["customer_id"] = df["customer_id"].astype(int)
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        df["estimated_delivery"] = pd.to_datetime(df["estimated_delivery"], errors="coerce")
        df["total_brl"] = pd.to_numeric(df["total_brl"], errors="coerce")
        return df

    def _load_order_items(self) -> pd.DataFrame:
        """Carrega order_items.csv."""
        csv_file = self.data_dir / "desafio_tecnico_ai_eng - order_items.csv"
        df = pd.read_csv(csv_file, encoding="utf-8")
        df["order_id"] = df["order_id"].astype(int)
        df["product_id"] = df["product_id"].astype(int)
        df["quantity"] = df["quantity"].astype(int)
        return df

    def _load_promotions(self) -> pd.DataFrame:
        """Carrega promotions.csv."""
        csv_file = self.data_dir / "desafio_tecnico_ai_eng - promotions.csv"
        df = pd.read_csv(csv_file, encoding="utf-8")
        df["promotion_id"] = df["promotion_id"].astype(int)
        df["product_id"] = df["product_id"].astype(int)
        df["discount_percent"] = df["discount_percent"].astype(float)
        df["is_active"] = df["is_active"].astype(bool)
        return df

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normaliza texto removendo acentos e convertendo para lowercase."""
        if not isinstance(text, str):
            return ""
        # Decomposição NFD: separa acentos
        nfd = unicodedata.normalize("NFD", text)
        # Remove acentos (classe 'Mn' = marca diacrítica)
        sem_acento = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        return sem_acento.lower().strip()

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normaliza número de telefone removendo símbolos."""
        if not isinstance(phone, str):
            return ""
        # Remove tudo que não é dígito
        digits = "".join(c for c in phone if c.isdigit())
        return digits

    @staticmethod
    def _parse_specs(specs_str) -> dict:
        """Parseia JSON string de specs."""
        if not isinstance(specs_str, str):
            return {}
        try:
            # Remove barras duplas de escape (se houver)
            specs_str = specs_str.replace('""', '"')
            return json.loads(specs_str)
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_category_name(self, category_id: int) -> Optional[str]:
        """Retorna nome da categoria por ID."""
        if self.categories is None:
            self.categories = self._load_categories()
        cat = self.categories[self.categories["category_id"] == category_id]
        if not cat.empty:
            return cat.iloc[0]["name"]
        return None

    def get_product_with_promotion(self, product_id: int) -> Optional[Dict]:
        """Retorna produto com preço ajustado por promoção ativa."""
        if self.products is None or self.promotions is None:
            self.load_all()

        prod = self.products[self.products["product_id"] == product_id]
        if prod.empty:
            return None

        prod_dict = prod.iloc[0].to_dict()
        base_price = prod_dict["price_brl"]

        # Verificar promoção ativa
        promo = self.promotions[
            (self.promotions["product_id"] == product_id)
            & (self.promotions["is_active"] == True)
        ]

        if not promo.empty:
            discount_percent = promo.iloc[0]["discount_percent"]
            promo_desc = promo.iloc[0]["description"]
            promo_price = base_price * (1 - discount_percent / 100)
            prod_dict["promotion"] = {
                "name": promo_desc,
                "discount_percent": discount_percent,
                "discounted_price": round(promo_price, 2),
            }
        else:
            prod_dict["promotion"] = None

        # Manual 3 e 6.2: PIX dá 5% sobre o preço de tabela e não acumula com promoção.
        prod_dict["pix_price"] = None if prod_dict["promotion"] else round(base_price * 0.95, 2)
        return prod_dict

    def verify_customer(
        self, customer_id: int, cpf: Optional[str] = None,
        email: Optional[str] = None, phone: Optional[str] = None
    ) -> bool:
        """
        Verifica identidade do cliente com 3 vias: CPF, email, ou phone.

        Nota: CSVs não contêm CPF, então apenas email/phone são verificáveis.
        """
        if self.customers is None:
            self.customers = self._load_customers()

        customer = self.customers[self.customers["customer_id"] == customer_id]
        if customer.empty:
            return False

        cust = customer.iloc[0]

        # Verificar email (case-insensitive)
        if email:
            if cust["email"].lower() == email.lower():
                return True

        # Verificar phone (apenas dígitos)
        if phone:
            phone_norm = self._normalize_phone(phone)
            if cust["phone_normalized"] == phone_norm:
                return True

        # CPF não está no CSV — retornar False sempre (ou True se implementado depois)
        # Por enquanto, apenas email/phone funcionam
        if cpf:
            # TODO: implementar busca de CPF se adicionado ao CSV
            pass

        return False


def main():
    """Teste básico de carregamento."""
    loader = DataLoader()
    loader.load_all()

    print("\n📊 Resumo dos Dados Carregados:")
    print(f"  • Produtos: {len(loader.products)} registros")
    print(f"  • Categorias: {len(loader.categories)} registros")
    print(f"  • Clientes: {len(loader.customers)} registros")
    print(f"  • Pedidos: {len(loader.orders)} registros")
    print(f"  • Itens de Pedido: {len(loader.order_items)} registros")
    print(f"  • Promoções: {len(loader.promotions)} registros (ativas: {loader.promotions['is_active'].sum()})")

    # Teste de busca de produto com promoção
    prod = loader.get_product_with_promotion(95)
    if prod:
        print(f"\n✅ Teste: Produto {prod['name']} (ID {prod['product_id']})")
        print(f"   Preço: R$ {prod['price_brl']}")
        if prod["promotion"]:
            print(f"   Promoção: {prod['promotion']['name']} ({prod['promotion']['discount_percent']}% OFF)")
            print(f"   Preço Final: R$ {prod['promotion']['discounted_price']}")


if __name__ == "__main__":
    main()
