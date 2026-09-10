"""
Mock del cliente de Nessie. Misma interfaz que RealNessieClient, así que
routers y servicios no notan la diferencia. Sirve para:

  1. Programar el resto del stack sin depender de tener ya la API key.
  2. Seguir la demo viva si Nessie se cae a media competencia.
  3. Escribir tests que no dependen de internet.

Guarda todo en memoria (se resetea si reinicias el server) — para un
hackathon es más que suficiente, no hace falta una base de datos aquí.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.nessie.base import NessieClient

_MERCHANTS = ["Oxxo", "Starbucks", "Spotify", "Uber", "Amazon MX", "HEB", "Netflix"]
_DESCRIPTIONS = ["Compra", "Suscripción mensual", "Transferencia", "Pago de servicio"]


def _seed_customers() -> list[dict[str, Any]]:
    return [
        {"_id": "cust_1", "first_name": "Diego", "last_name": "Hackathon"},
        {"_id": "cust_2", "first_name": "Equipo", "last_name": "MuchachosIdk"},
    ]


def _seed_accounts() -> dict[str, list[dict[str, Any]]]:
    return {
        "cust_1": [
            {
                "_id": "acc_1",
                "type": "Checking",
                "nickname": "Cuenta principal",
                "balance": 12500.0,
                "customer_id": "cust_1",
            },
            {
                "_id": "acc_2",
                "type": "Savings",
                "nickname": "Ahorro",
                "balance": 30800.0,
                "customer_id": "cust_1",
            },
        ]
    }


class MockNessieClient(NessieClient):
    def __init__(self):
        self._customers = _seed_customers()
        self._accounts = _seed_accounts()
        self._transactions: dict[str, list[dict[str, Any]]] = {
            "acc_1": self._generate_history("acc_1", days=14),
            "acc_2": self._generate_history("acc_2", days=14),
        }

    def _generate_history(self, account_id: str, days: int) -> list[dict[str, Any]]:
        history = []
        for i in range(days):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            history.append(
                {
                    "id": str(uuid.uuid4()),
                    "type": random.choice(["purchase", "transfer", "deposit"]),
                    "amount": round(random.uniform(50, 900), 2),
                    "description": f"{random.choice(_DESCRIPTIONS)} - {random.choice(_MERCHANTS)}",
                    "date": date.strftime("%Y-%m-%d"),
                    "status": "completed",
                }
            )
        return history

    async def list_customers(self) -> list[dict[str, Any]]:
        return self._customers

    async def list_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        return self._accounts.get(customer_id, [])

    async def get_account(self, account_id: str) -> dict[str, Any]:
        for accounts in self._accounts.values():
            for account in accounts:
                if account["_id"] == account_id:
                    return account
        raise KeyError(f"No existe la cuenta mock '{account_id}'")

    async def list_transactions(self, account_id: str) -> list[dict[str, Any]]:
        transactions = self._transactions.get(account_id, [])
        return sorted(transactions, key=lambda tx: tx["date"], reverse=True)

    async def create_purchase(
        self,
        account_id: str,
        merchant_id: str,
        amount: float,
        description: str = "",
    ) -> dict[str, Any]:
        transaction = {
            "id": str(uuid.uuid4()),
            "type": "purchase",
            "amount": amount,
            "description": description or f"Compra en {merchant_id}",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "completed",
        }
        self._transactions.setdefault(account_id, []).insert(0, transaction)
        return transaction
