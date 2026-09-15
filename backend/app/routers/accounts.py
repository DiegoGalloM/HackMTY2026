from fastapi import APIRouter, Depends, HTTPException

from app.http_hardening import require_legacy_nessie_routes
from app.models.schemas import Account
from app.nessie import get_nessie_client
from app.nessie.base import NessieClient

# Passthrough a Nessie de la plantilla original: público y sin uso en el
# frontend, así que en producción responde 404 (ver app/http_hardening.py).
router = APIRouter(prefix="/accounts", tags=["accounts"], dependencies=[Depends(require_legacy_nessie_routes)])


@router.get("/customer/{customer_id}", response_model=list[Account])
async def list_customer_accounts(
    customer_id: str,
    nessie: NessieClient = Depends(get_nessie_client),  # noqa: B008
):
    raw_accounts = await nessie.list_accounts(customer_id)
    return [
        Account(
            id=a["_id"],
            type=a.get("type", "unknown"),
            nickname=a.get("nickname"),
            balance=a.get("balance", 0.0),
        )
        for a in raw_accounts
    ]


@router.get("/{account_id}", response_model=Account)
async def get_account(
    account_id: str,
    nessie: NessieClient = Depends(get_nessie_client),  # noqa: B008
):
    try:
        a = await nessie.get_account(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Account(
        id=a["_id"],
        type=a.get("type", "unknown"),
        nickname=a.get("nickname"),
        balance=a.get("balance", 0.0),
    )
