"""Ferramentas para consulta de pedidos (com verificação de identidade)."""

from typing import List, Dict, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import DataLoader


class OrderTools:
    def __init__(self, loader: DataLoader):
        self.loader = loader

    def check_order_status(
        self,
        order_id: int,
        customer_verification: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Consulta status de um pedido (com verificação de identidade).

        Requer verificação por email OU phone (3 vias).

        Args:
            order_id: ID do pedido
            customer_verification: Email ou telefone para verificação

        Returns:
            Dicionário com status, tracking, entrega estimada, etc.
            Retorna None se pedido não encontrado ou verificação falhar.
        """
        if self.loader.orders is None or self.loader.customers is None:
            self.loader.load_all()

        # Encontrar pedido
        order = self.loader.orders[self.loader.orders["order_id"] == order_id]
        if order.empty:
            return None

        order_row = order.iloc[0]
        customer_id = int(order_row["customer_id"])

        # VERIFICAÇÃO OBRIGATÓRIA: email ou phone
        if not customer_verification:
            return {
                "error": "Verificação obrigatória",
                "message": "Para acessar seu pedido, precisamos verificar sua identidade. "
                           "Por favor, forneça seu email ou telefone.",
                "status": "verification_required",
            }

        # Tentar verificar por email ou phone
        if not self._verify_customer(customer_id, customer_verification):
            return {
                "error": "Verificação falhou",
                "message": "Email ou telefone não correspondem ao pedido. "
                           "Tente novamente ou entre em contato conosco.",
                "status": "verification_failed",
            }

        # Verificação OK, retornar dados do pedido
        items = self.loader.order_items[
            self.loader.order_items["order_id"] == order_id
        ]

        order_dict = {
            "order_id": int(order_row["order_id"]),
            "order_date": str(order_row["order_date"].date()) if pd.notna(order_row["order_date"]) else "N/A",
            "status": order_row["status"],
            "total_brl": round(order_row["total_brl"], 2),
            "payment_method": order_row["payment_method"],
            "items": len(items),
            "tracking_code": order_row["tracking_code"] if pd.notna(order_row["tracking_code"]) else None,
            "estimated_delivery": str(order_row["estimated_delivery"].date()) if pd.notna(order_row["estimated_delivery"]) else None,
            "notes": order_row["notes"] if pd.notna(order_row["notes"]) else None,
        }

        # Adicionar descrição do status
        order_dict["status_description"] = self._get_status_description(order_row["status"])

        return order_dict

    def get_customer_orders(self, customer_verification: str) -> List[Dict]:
        """
        Retorna todos os pedidos de um cliente (após verificação por email/phone).

        Args:
            customer_verification: Email ou telefone do cliente

        Returns:
            Lista de pedidos do cliente (resumido)
        """
        if self.loader.orders is None or self.loader.customers is None:
            self.loader.load_all()

        # Encontrar cliente por email ou phone
        customer_id = self._find_customer_by_verification(customer_verification)
        if customer_id is None:
            return []

        # Buscar pedidos deste cliente
        orders = self.loader.orders[self.loader.orders["customer_id"] == customer_id]

        output = []
        for _, row in orders.iterrows():
            output.append({
                "order_id": int(row["order_id"]),
                "order_date": str(row["order_date"].date()) if pd.notna(row["order_date"]) else "N/A",
                "status": row["status"],
                "total_brl": round(row["total_brl"], 2),
                "status_description": self._get_status_description(row["status"]),
            })

        # Ordenar por data (mais recente primeiro)
        output = sorted(output, key=lambda x: x["order_date"], reverse=True)
        return output

    def _verify_customer(self, customer_id: int, verification: str) -> bool:
        """Verifica identidade do cliente por email ou phone."""
        # Tentar como email
        if "@" in verification:
            return self.loader.verify_customer(customer_id, email=verification)
        else:
            # Tentar como phone
            return self.loader.verify_customer(customer_id, phone=verification)

    def _find_customer_by_verification(self, verification: str) -> Optional[int]:
        """Encontra customer_id a partir de email ou phone."""
        if self.loader.customers is None:
            self.loader.customers = self.loader._load_customers()

        if "@" in verification:
            # Buscar por email
            customer = self.loader.customers[
                self.loader.customers["email"].str.lower() == verification.lower()
            ]
        else:
            # Buscar por phone (normalizado)
            phone_norm = self.loader._normalize_phone(verification)
            customer = self.loader.customers[
                self.loader.customers["phone_normalized"] == phone_norm
            ]

        if not customer.empty:
            return int(customer.iloc[0]["customer_id"])
        return None

    @staticmethod
    def _get_status_description(status: str) -> str:
        """Retorna descrição amigável do status do pedido."""
        descriptions = {
            "pending": "Seu pedido foi recebido e está aguardando processamento. 📋",
            "confirmed": "Seu pedido foi confirmado e em breve será enviado. ✅",
            "shipped": "Seu pedido está a caminho! 📦",
            "delivered": "Seu pedido foi entregue com sucesso! 🎉",
            "cancelled": "Seu pedido foi cancelado. ❌",
        }
        return descriptions.get(status, f"Status: {status}")


# Importar pandas para verificações de NaN
import pandas as pd
