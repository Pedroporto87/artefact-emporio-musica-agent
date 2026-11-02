"""Carga e limpeza dos CSVs fornecidos pela loja."""

import json
import unicodedata
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

CSV_PREFIX = "desafio_tecnico_ai_eng - "


class DataLoader:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent / "data"
        self.products = None
        self.categories = None
        self.customers = None
        self.orders = None
        self.order_items = None
        self.promotions = None

    def load_all(self):
        self.products = self._load_products()
        self.categories = self._read("categories").astype({"category_id": int})
        self.customers = self._load_customers()
        self.orders = self._load_orders()
        self.order_items = self._read("order_items").astype({"order_id": int, "product_id": int, "quantity": int})
        self.promotions = self._read("promotions").astype(
            {"promotion_id": int, "product_id": int, "discount_percent": float, "is_active": bool}
        )

    def _read(self, table: str) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / f"{CSV_PREFIX}{table}.csv", encoding="utf-8")

    def _load_products(self) -> pd.DataFrame:
        df = self._read("products").astype({"product_id": int, "category_id": int, "stock_quantity": int})
        df["price_brl"] = pd.to_numeric(df["price_brl"], errors="coerce")
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["specs"] = df["specs"].apply(self._parse_specs)
        df["name_normalized"] = df["name"].apply(self._normalize_text)
        return df.fillna({"status": "active", "description": ""})

    def _load_customers(self) -> pd.DataFrame:
        df = self._read("customers").astype({"customer_id": int})
        df["phone_normalized"] = df["phone"].apply(self._normalize_phone)
        return df

    def _load_orders(self) -> pd.DataFrame:
        df = self._read("orders").astype({"order_id": int, "customer_id": int})
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        df["estimated_delivery"] = pd.to_datetime(df["estimated_delivery"], errors="coerce")
        df["total_brl"] = pd.to_numeric(df["total_brl"], errors="coerce")
        return df

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Minúsculas e sem acento, para busca: "Violão" -> "violao"."""
        if not isinstance(text, str):
            return ""
        decomposed = unicodedata.normalize("NFD", text)
        return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower().strip()

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        if not isinstance(phone, str):
            return ""
        return "".join(c for c in phone if c.isdigit())

    @staticmethod
    def _parse_specs(specs: str) -> dict:
        if not isinstance(specs, str):
            return {}
        try:
            return json.loads(specs)
        except json.JSONDecodeError:
            return {}

    def get_category_name(self, category_id: int) -> Optional[str]:
        match = self.categories[self.categories["category_id"] == category_id]
        return None if match.empty else match.iloc[0]["name"]

    def get_product_with_promotion(self, product_id: int) -> Optional[Dict]:
        """Produto com a promoção ativa (se houver) e o preço no PIX já calculados."""
        match = self.products[self.products["product_id"] == product_id]
        if match.empty:
            return None

        product = match.iloc[0].to_dict()
        base_price = product["price_brl"]
        promo = self.promotions[(self.promotions["product_id"] == product_id) & self.promotions["is_active"]]

        if promo.empty:
            product["promotion"] = None
        else:
            discount = promo.iloc[0]["discount_percent"]
            product["promotion"] = {
                "name": promo.iloc[0]["description"],
                "discount_percent": discount,
                "discounted_price": round(base_price * (1 - discount / 100), 2),
            }

        # Manual 3 e 6.2: PIX dá 5% sobre o preço de tabela e não acumula com promoção.
        product["pix_price"] = None if product["promotion"] else round(base_price * 0.95, 2)
        return product

    def verify_customer(self, customer_id: int, email: Optional[str] = None, phone: Optional[str] = None) -> bool:
        """Confere e-mail ou telefone com o cadastro. Os CSVs não têm CPF."""
        match = self.customers[self.customers["customer_id"] == customer_id]
        if match.empty:
            return False
        customer = match.iloc[0]
        if email and customer["email"].lower() == email.strip().lower():
            return True
        return bool(phone) and customer["phone_normalized"] == self._normalize_phone(phone)
