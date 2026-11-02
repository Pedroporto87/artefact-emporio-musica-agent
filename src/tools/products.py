"""Ferramentas de catálogo: busca, detalhes, promoções e alternativas."""

import re
from typing import Dict, List, Optional

import pandas as pd
from fuzzywuzzy import fuzz

from data_loader import DataLoader

STOPWORDS = {"de", "do", "da", "e"}


class ProductTools:
    def __init__(self, loader: DataLoader):
        self.loader = loader

    def _summary(self, row: pd.Series, with_description: bool = False) -> Dict:
        product_id = int(row["product_id"])
        priced = self.loader.get_product_with_promotion(product_id)
        item = {
            "product_id": product_id,
            "name": row["name"],
            "price_brl": round(float(row["price_brl"]), 2),
            "stock_quantity": int(row["stock_quantity"]),
            "pix_price": priced["pix_price"],
        }
        if priced["promotion"]:
            item["promotion"] = priced["promotion"]
        if with_description:
            item["description"] = row["description"]
            item["category"] = self.loader.get_category_name(int(row["category_id"]))
        return item

    def categories_with_products(self) -> List[str]:
        ids = set(self.loader.products["category_id"].unique())
        cats = self.loader.categories
        return cats[cats["category_id"].isin(ids)]["name"].tolist()

    def search_products(
        self,
        category_name: Optional[str] = None,
        brand: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        in_stock_only: bool = True,
        limit: int = 10,
        order: str = "menor_preco",
    ) -> Dict:
        """O "status" separa "a loja não vende isso" de "vende, mas acabou": com lista vazia o modelo confundia os dois."""
        results = self.loader.products

        if category_name:
            cat_id = self._find_category_id(category_name)
            if cat_id is None:
                return {
                    "status": "nao_vendemos",
                    "mensagem": (
                        f"A loja não trabalha com '{category_name}'. Responda apenas que não trabalhamos com "
                        "isso e ofereça as categorias abaixo. NÃO cite nenhum produto ou preço sem antes "
                        "chamar search_products para a categoria escolhida."
                    ),
                    "categorias_que_vendemos": self.categories_with_products(),
                    "produtos": [],
                }
            results = results[results["category_id"] == cat_id]
            if results.empty:
                return {
                    "status": "categoria_sem_produtos",
                    "mensagem": (
                        f"A loja trabalha com '{self.loader.get_category_name(cat_id)}', mas não há modelos "
                        "dessa categoria no catálogo agora. NÃO cite produtos nem preços."
                    ),
                    "categorias_que_vendemos": self.categories_with_products(),
                    "produtos": [],
                }

        if brand:
            results = results[results["name_normalized"].str.contains(self.loader._normalize_text(brand), regex=False)]
        if price_min is not None:
            results = results[results["price_brl"] >= price_min]
        if price_max is not None:
            results = results[results["price_brl"] <= price_max]
        if results.empty:
            return {
                "status": "nenhum_resultado",
                "mensagem": "Nenhum produto do catálogo atende a esses filtros (marca/preço).",
                "produtos": [],
            }

        if in_stock_only:
            in_stock = results[results["stock_quantity"] > 0]
            if in_stock.empty:
                return {
                    "status": "sem_estoque",
                    "mensagem": "Existem produtos com esses filtros, mas todos estão sem estoque.",
                    "produtos_sem_estoque": [
                        {"product_id": int(r["product_id"]), "name": r["name"]} for _, r in results.head(limit).iterrows()
                    ],
                    "produtos": [],
                }
            results = in_stock

        # A ordem é decidida aqui: com a lista cortada em `limit`, o modelo não acha o "mais caro"
        # se receber só os mais baratos.
        results = results.sort_values("price_brl", ascending=(order != "maior_preco"))
        shown = [self._summary(row, with_description=True) for _, row in results.head(limit).iterrows()]
        return {
            "status": "ok",
            "ordenado_por": "maior preço primeiro" if order == "maior_preco" else "menor preço primeiro",
            "total_encontrado": len(results),
            "mostrando": len(shown),
            "produtos": shown,
        }

    def get_product_details(self, product_id: int) -> Optional[Dict]:
        product = self.loader.get_product_with_promotion(product_id)
        if not product:
            return None
        return {
            "product_id": int(product["product_id"]),
            "name": product["name"],
            "price_brl": round(float(product["price_brl"]), 2),
            "stock_quantity": int(product["stock_quantity"]),
            "description": product["description"],
            "category": self.loader.get_category_name(int(product["category_id"])),
            "specs": product["specs"],
            "promotion": product["promotion"],
            "pix_price": product["pix_price"],
        }

    def list_active_promotions(self) -> List[Dict]:
        active = self.loader.promotions[self.loader.promotions["is_active"]]
        products = self.loader.products.set_index("product_id")
        promotions = []
        for _, promo in active.iterrows():
            if promo["product_id"] not in products.index:
                continue
            price = float(products.loc[promo["product_id"], "price_brl"])
            promotions.append({
                "product_id": int(promo["product_id"]),
                "product_name": products.loc[promo["product_id"], "name"],
                "promotion_name": promo["description"],
                "discount_percent": float(promo["discount_percent"]),
                "original_price": round(price, 2),
                "final_price": round(price * (1 - promo["discount_percent"] / 100), 2),
            })
        return sorted(promotions, key=lambda p: p["discount_percent"], reverse=True)

    def suggest_alternatives(self, product_id: int, max_price: Optional[float] = None) -> List[Dict]:
        """Mesma categoria e em estoque; sem max_price, preço até 20% acima ou abaixo do original."""
        products = self.loader.products
        original = products[products["product_id"] == product_id]
        if original.empty:
            return []
        base_price = original.iloc[0]["price_brl"]
        low, high = (0, max_price) if max_price is not None else (base_price * 0.8, base_price * 1.2)
        similar = products[
            (products["category_id"] == original.iloc[0]["category_id"])
            & (products["product_id"] != product_id)
            & (products["stock_quantity"] > 0)
            & products["price_brl"].between(low, high)
        ].sort_values("price_brl").head(5)
        return [self._summary(row) for _, row in similar.iterrows()]

    def search_by_name(self, product_name: str, threshold: int = 80) -> Dict:
        # token_set_ratio aceita nome parcial ("takamine gd20" casa com o nome completo);
        # sem hífen, "gf3d" casa com "GF-3D".
        query = self.loader._normalize_text(product_name).replace("-", "")
        matches = []
        for _, row in self.loader.products.iterrows():
            score = fuzz.token_set_ratio(query, row["name_normalized"].replace("-", ""))
            if score >= threshold:
                matches.append({**self._summary(row), "similarity_score": score})
        if not matches:
            return {
                "status": "nao_encontrado",
                "mensagem": (
                    f"Nenhum produto chamado '{product_name}' no catálogo. Não diga 'sem estoque'. Se for um "
                    "tipo de instrumento, use search_products com a categoria para saber se a loja trabalha "
                    "com ele. NÃO cite produto ou preço sem consultar uma ferramenta."
                ),
                "categorias_que_vendemos": self.categories_with_products(),
                "produtos": [],
            }
        return {"status": "ok", "produtos": sorted(matches, key=lambda m: m["similarity_score"], reverse=True)}

    def _find_category_id(self, category_name: str) -> Optional[int]:
        query = self._singularize(self.loader._normalize_text(category_name))
        categories = self.loader.categories
        for _, row in categories.iterrows():
            # Limiar alto: com 80, "violinos" casava com "violoes".
            if fuzz.token_set_ratio(query, self._singularize(self.loader._normalize_text(row["name"]))) >= 90:
                return int(row["category_id"])

        # Instrumento citado só na descrição: "violino" está em "Cordas Orquestrais".
        query_words = set(self._words(category_name)) - STOPWORDS
        for _, row in categories.iterrows():
            if query_words and query_words <= set(self._words(row["description"])):
                return int(row["category_id"])
        return None

    def _words(self, text: str) -> List[str]:
        return self._singularize(re.sub(r"[^a-z ]", " ", self.loader._normalize_text(text))).split()

    @staticmethod
    def _singularize(text: str) -> str:
        """Plural simples do português: violoes -> violao, guitarras -> guitarra."""
        words = []
        for w in text.split():
            if w.endswith(("oes", "aes")):
                w = w[:-3] + "ao"
            elif w.endswith("s") and len(w) > 3:
                w = w[:-1]
            words.append(w)
        return " ".join(words)
