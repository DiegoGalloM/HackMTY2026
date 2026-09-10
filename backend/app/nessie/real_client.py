"""
Cliente real contra api.nessieisreal.com.

⚠️ Los nombres de campo de abajo son los históricos de la API pública de
Nessie, pero Capital One la ha modificado entre ediciones de hackathon.
En cuanto tengan su API key, abran la documentación interactiva
(link "Interactive Documentation" en http://api.nessieisreal.com/) y
comparen contra un GET real antes de confiar en esto a ciegas — es
exactamente el tipo de cosa que el equipo de John Deere aprendió a
verificar (dato de fuente no oficial) antes de usarlo en el pitch.
"""

from datetime import datetime, timezone
from typing import Any

import httpx

from app.nessie.base import NessieClient


class RealNessieClient(NessieClient):
    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    async def _get(self, client: httpx.AsyncClient, path: str) -> Any:
        response = await client.get(self._url(path), params={"key": self._api_key})
        response.raise_for_status()
        return response.json()

    async def list_customers(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            return await self._get(client, "/customers")

    async def list_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            return await self._get(client, f"/customers/{customer_id}/accounts")

    async def get_account(self, account_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            return await self._get(client, f"/accounts/{account_id}")

    async def list_transactions(self, account_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            purchases = await self._get(client, f"/accounts/{account_id}/purchases")
            transfers = await self._get(client, f"/accounts/{account_id}/transfers")
            deposits = await self._get(client, f"/accounts/{account_id}/deposits")
            withdrawals = await self._get(client, f"/accounts/{account_id}/withdrawals")

        normalized = [
            *(_normalize(p, "purchase", "purchase_date") for p in purchases),
            *(_normalize(t, "transfer", "transaction_date") for t in transfers),
            *(_normalize(d, "deposit", "transaction_date") for d in deposits),
            *(_normalize(w, "withdrawal", "transaction_date") for w in withdrawals),
        ]
        normalized.sort(key=lambda tx: tx["date"], reverse=True)
        return normalized

    async def create_purchase(
        self,
        account_id: str,
        merchant_id: str,
        amount: float,
        description: str = "",
    ) -> dict[str, Any]:
        payload = {
            "merchant_id": merchant_id,
            "medium": "balance",
            "purchase_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "amount": amount,
            "description": description,
            "status": "completed",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self._url(f"/accounts/{account_id}/purchases"),
                params={"key": self._api_key},
                json=payload,
            )
            response.raise_for_status()
            return response.json()


def _normalize(raw: dict[str, Any], tx_type: str, date_field: str) -> dict[str, Any]:
    return {
        "id": raw.get("_id"),
        "type": tx_type,
        "amount": raw.get("amount", 0.0),
        "description": raw.get("description", ""),
        "date": raw.get(date_field, ""),
        "status": raw.get("status", "unknown"),
    }
