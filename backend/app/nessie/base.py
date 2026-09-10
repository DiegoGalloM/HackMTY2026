"""
Interfaz común para hablar con "el proveedor de datos bancarios", sea la
API real de Nessie o el mock local.

Por qué esto importa: si Nessie se cae (pasó en HackMTY 2025, ver README),
lo único que cambian es `USE_MOCK_NESSIE=true` en el .env — routers y
servicios nunca importan httpx directamente, siempre dependen de esta
interfaz vía `get_nessie_client()` (ver __init__.py).
"""

from abc import ABC, abstractmethod
from typing import Any


class NessieClient(ABC):
    @abstractmethod
    async def list_customers(self) -> list[dict[str, Any]]:
        """Todos los clientes visibles con tu API key."""

    @abstractmethod
    async def list_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        """Cuentas de un cliente (checking, savings, credit card...)."""

    @abstractmethod
    async def get_account(self, account_id: str) -> dict[str, Any]:
        """Detalle de una cuenta, incluyendo balance actual."""

    @abstractmethod
    async def list_transactions(self, account_id: str) -> list[dict[str, Any]]:
        """
        Vista normalizada: junta purchases + transfers + deposits +
        withdrawals de Nessie (que en la API real viven en 4 endpoints
        distintos con formas distintas) en una sola lista con esta forma:

            {
                "id": str,
                "type": "purchase" | "transfer" | "deposit" | "withdrawal",
                "amount": float,
                "description": str,
                "date": str,  # ISO 8601
                "status": str,
            }

        Ordenada por fecha descendente (más reciente primero).
        """

    @abstractmethod
    async def create_purchase(
        self,
        account_id: str,
        merchant_id: str,
        amount: float,
        description: str = "",
    ) -> dict[str, Any]:
        """
        Crea una compra nueva. Útil para *simular* actividad en tiempo real:
        un script/cron que va llamando esto cada N segundos con datos
        variados hace que el dashboard se sienta "vivo" en la demo.
        """
