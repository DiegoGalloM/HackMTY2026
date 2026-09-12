from fastapi import APIRouter, Depends

from app.models.schemas import NewPurchase, Transaction
from app.nessie import get_nessie_client
from app.nessie.base import NessieClient

router = APIRouter(prefix="/accounts/{account_id}/transactions", tags=["transactions"])


@router.get("", response_model=list[Transaction])
async def list_transactions(
    account_id: str,
    nessie: NessieClient = Depends(get_nessie_client),  # noqa: B008
):
    raw = await nessie.list_transactions(account_id)
    return [Transaction(**tx) for tx in raw]


@router.post("/simulate", response_model=Transaction)
async def simulate_purchase(
    account_id: str,
    purchase: NewPurchase,
    nessie: NessieClient = Depends(get_nessie_client),  # noqa: B008
):
    """
    Crea una compra nueva ahora mismo. Pensado para un botón de "generar
    actividad" en la demo, o para un script que lo llame cada N segundos
    y así el dashboard/app de escritorio se vea actualizándose en vivo
    frente a los jueces sin depender de datos reales de Nessie.
    """
    raw = await nessie.create_purchase(
        account_id=account_id,
        merchant_id=purchase.merchant_id,
        amount=purchase.amount,
        description=purchase.description,
    )
    return Transaction(**raw)
