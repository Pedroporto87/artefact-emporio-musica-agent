"""Ferramentas para busca e consulta de produtos."""

from typing import List, Dict, Optional
from fuzzywuzzy import fuzz
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import DataLoader


class ProductTools:
    def __init__(self, loader: DataLoader):
        self.loader = loader

    def search_products(
        self,
        category_name: Optional[str] = None,
        brand: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        in_stock_only: bool = True,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Busca produtos com filtros.

        Args:
            category_name: Nome da categoria (ex: "Violões")
            brand: Marca/fabricante (ex: "Yamaha")
            price_min: Preço mínimo em R$
            price_max: Preço máximo em R$
            in_stock_only: Se True, apenas produtos com estoque > 0
            limit: Número máximo de resultados

        Returns:
            Lista de produtos com id, name, price_brl, stock, description, promotion
        """
        if self.loader.products is None:
            self.loader.load_all()

        results = self.loader.products.copy()

        # Filtro por categoria
        if category_name:
            cat_id = self._find_category_id(category_name)
            if cat_id:
                results = results[results["category_id"] == cat_id]
            else:
                return []  # Categoria não encontrada

        # Filtro por marca (busca no nome normalizado)
        if brand:
            brand_norm = self.loader._normalize_text(brand)
            results = results[
                results["name_normalized"].str.contains(brand_norm, regex=False)
            ]

        # Filtro por preço
        if price_min is not None:
            results = results[results["price_brl"] >= price_min]
        if price_max is not None:
            results = results[results["price_brl"] <= price_max]

        # Filtro por estoque
        if in_stock_only:
            results = results[results["stock_quantity"] > 0]

        # Ordenar por preço
        results = results.sort_values("price_brl")

        # Limitar resultados
        results = results.head(limit)

        # Formatar resposta
        output = []
        for _, row in results.iterrows():
            prod = {
                "product_id": int(row["product_id"]),
                "name": row["name"],
                "price_brl": round(row["price_brl"], 2),
                "stock_quantity": int(row["stock_quantity"]),
                "description": row["description"],
                "category": self.loader.get_category_name(row["category_id"]),
            }

            # Adicionar promoção se ativa
            prod_with_promo = self.loader.get_product_with_promotion(int(row["product_id"]))
            if prod_with_promo and prod_with_promo["promotion"]:
                prod["promotion"] = prod_with_promo["promotion"]

            output.append(prod)

        return output

    def get_product_details(self, product_id: int) -> Optional[Dict]:
        """
        Retorna detalhes completos de um produto.

        Args:
            product_id: ID do produto

        Returns:
            Dicionário com: id, name, price, stock, category, specs, promotion (se ativo)
        """
        if self.loader.products is None:
            self.loader.load_all()

        prod = self.loader.get_product_with_promotion(product_id)
        if not prod:
            return None

        # Formatar resposta
        return {
            "product_id": int(prod["product_id"]),
            "name": prod["name"],
            "price_brl": round(prod["price_brl"], 2),
            "stock_quantity": int(prod["stock_quantity"]),
            "description": prod["description"],
            "category": self.loader.get_category_name(prod["category_id"]),
            "specs": prod.get("specs", {}),
            "promotion": prod.get("promotion"),
            "status": prod.get("status", "active"),
        }

    def list_active_promotions(self) -> List[Dict]:
        """
        Retorna todas as promoções vigentes.

        Returns:
            Lista de promoções ativas com: product_id, name, discount_percent
        """
        if self.loader.promotions is None or self.loader.products is None:
            self.loader.load_all()

        active = self.loader.promotions[self.loader.promotions["is_active"] == True]

        output = []
        for _, row in active.iterrows():
            prod = self.loader.products[
                self.loader.products["product_id"] == row["product_id"]
            ]
            if not prod.empty:
                output.append({
                    "product_id": int(row["product_id"]),
                    "product_name": prod.iloc[0]["name"],
                    "promotion_name": row["description"],
                    "discount_percent": float(row["discount_percent"]),
                    "original_price": round(prod.iloc[0]["price_brl"], 2),
                    "final_price": round(
                        prod.iloc[0]["price_brl"] * (1 - row["discount_percent"] / 100), 2
                    ),
                })

        return sorted(output, key=lambda x: x["discount_percent"], reverse=True)

    def suggest_alternatives(
        self, product_id: int, max_price: Optional[float] = None
    ) -> List[Dict]:
        """
        Sugere produtos similares (mesma categoria, estoque > 0).
        Útil quando produto solicitado está sem estoque.

        Args:
            product_id: ID do produto indisponível
            max_price: Limite de preço (padrão: ± 20% do preço original)

        Returns:
            Lista de alternativas similares
        """
        if self.loader.products is None:
            self.loader.load_all()

        original = self.loader.products[
            self.loader.products["product_id"] == product_id
        ]
        if original.empty:
            return []

        orig = original.iloc[0]
        category_id = orig["category_id"]
        base_price = orig["price_brl"]

        # Definir faixa de preço se não especificado
        if max_price is None:
            price_min = base_price * 0.8
            price_max = base_price * 1.2
        else:
            price_min = 0
            price_max = max_price

        # Buscar similares (mesma categoria, em estoque, preço próximo)
        alternatives = self.loader.products[
            (self.loader.products["category_id"] == category_id)
            & (self.loader.products["product_id"] != product_id)
            & (self.loader.products["stock_quantity"] > 0)
            & (self.loader.products["price_brl"] >= price_min)
            & (self.loader.products["price_brl"] <= price_max)
        ].sort_values("price_brl")

        # Limitar a 5 alternativas
        alternatives = alternatives.head(5)

        output = []
        for _, row in alternatives.iterrows():
            prod = {
                "product_id": int(row["product_id"]),
                "name": row["name"],
                "price_brl": round(row["price_brl"], 2),
                "stock_quantity": int(row["stock_quantity"]),
                "reason": f"Mesma categoria, {row['stock_quantity']} em estoque",
            }

            # Adicionar promoção se ativa
            prod_with_promo = self.loader.get_product_with_promotion(int(row["product_id"]))
            if prod_with_promo and prod_with_promo["promotion"]:
                prod["promotion"] = prod_with_promo["promotion"]

            output.append(prod)

        return output

    def search_by_name(self, product_name: str, threshold: int = 80) -> List[Dict]:
        """
        Busca produtos por nome com fuzzy matching.

        Args:
            product_name: Nome (parcial ou completo)
            threshold: Score de similaridade (0-100, padrão 80)

        Returns:
            Produtos encontrados, ordenados por similaridade
        """
        if self.loader.products is None:
            self.loader.load_all()

        name_norm = self.loader._normalize_text(product_name)
        results = []

        for _, row in self.loader.products.iterrows():
            # token_set_ratio aceita nomes parciais: "takamine gd20" casa com o nome completo do catálogo
            score = fuzz.token_set_ratio(name_norm.replace("-", ""), row["name_normalized"].replace("-", ""))
            if score >= threshold:
                prod = {
                    "product_id": int(row["product_id"]),
                    "name": row["name"],
                    "price_brl": round(row["price_brl"], 2),
                    "stock_quantity": int(row["stock_quantity"]),
                    "similarity_score": score,
                }

                # Adicionar promoção se ativa
                prod_with_promo = self.loader.get_product_with_promotion(int(row["product_id"]))
                if prod_with_promo and prod_with_promo["promotion"]:
                    prod["promotion"] = prod_with_promo["promotion"]

                results.append(prod)

        # Ordenar por similaridade (descendente)
        results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)
        return results

    def _find_category_id(self, category_name: str) -> Optional[int]:
        """Encontra ID da categoria por nome (fuzzy)."""
        if self.loader.categories is None:
            self.loader.categories = self.loader._load_categories()

        cat_norm = self.loader._normalize_text(category_name)

        for _, row in self.loader.categories.iterrows():
            cat_name_norm = self.loader._normalize_text(row["name"])
            score = fuzz.ratio(cat_norm, cat_name_norm)
            if score >= 80:
                return int(row["category_id"])

        return None
