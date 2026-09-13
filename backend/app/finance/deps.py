"""
Contexto financiero por request: todos los servicios ya atados al negocio
del usuario autenticado. Los routers piden `Depends(get_finance_context)` y
no pueden construir un Repo para otro business_id.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from fastapi import Depends

from app.config import Settings, get_settings
from app.db import get_db
from app.db.base import Database
from app.finance import cache
from app.finance.accounting import AccountingService
from app.finance.analytics import AnalyticsService
from app.finance.assistant import Assistant
from app.finance.catalog import CatalogService
from app.finance.inventory import InventoryService
from app.finance.llm import LLMProvider, build_llm
from app.finance.purchases import (
    DemoTransactionProvider,
    NessieTransactionProvider,
    PurchaseService,
    TransactionProvider,
)
from app.finance.repo import Repo
from app.finance.sales import SalesService
from app.models.schemas import StoredUser
from app.routers.deps import require_owner
from app.storage import get_store
from app.storage.base import ProfileStore


@dataclass
class FinanceContext:
    business_id: str
    business_name: str
    db: Database
    settings: Settings
    profile: dict[str, Any] | None = None
    llm: LLMProvider | None = None

    @cached_property
    def repo(self) -> Repo:
        return Repo(self.db, self.business_id)

    @cached_property
    def accounting(self) -> AccountingService:
        return AccountingService(self.repo)

    @cached_property
    def inventory(self) -> InventoryService:
        return InventoryService(self.repo, self.accounting)

    @cached_property
    def catalog(self) -> CatalogService:
        return CatalogService(self.repo, self.inventory)

    @cached_property
    def sales(self) -> SalesService:
        return SalesService(self.repo, self.accounting, self.inventory, self.catalog)

    @property
    def category(self) -> str | None:
        return (self.profile or {}).get("category")

    @cached_property
    def purchases(self) -> PurchaseService:
        return PurchaseService(self.repo, self.accounting, self.inventory, self.category)

    @cached_property
    def analytics(self) -> AnalyticsService:
        return AnalyticsService(self.repo, self.accounting, self.inventory, self.sales, self.purchases, self.category)

    @cached_property
    def assistant(self) -> Assistant:
        return Assistant(
            analytics=self.analytics,
            sales=self.sales,
            inventory=self.inventory,
            catalog=self.catalog,
            purchases=self.purchases,
            profile=self.profile,
            business_name=self.business_name,
            llm=self.llm or build_llm(self.settings, self.db),
        )

    @cached_property
    def transaction_provider(self) -> TransactionProvider:
        if self.settings.transaction_provider == "nessie":
            from app.nessie import get_nessie_client

            return NessieTransactionProvider(get_nessie_client())
        return DemoTransactionProvider()

    def ensure_ready(self) -> None:
        """Un negocio recién registrado no tiene catálogo de cuentas todavía."""
        if not self.accounting.has_chart():
            self.accounting.ensure_chart_of_accounts(self.category)


async def get_finance_context(
    owner: StoredUser = Depends(require_owner),  # noqa: B008
    db: Database = Depends(get_db),  # noqa: B008
    store: ProfileStore = Depends(get_store),  # noqa: B008
) -> FinanceContext:
    # El perfil se cachea unos minutos: se lee en cada request y sólo cambia
    # al guardar el onboarding (que invalida la entrada).
    key = ("profile", id(store), owner.user_id)
    profile = cache.get(key, lambda: None)
    if profile is None:
        profile = await store.get_profile(owner.user_id)
        if profile is not None:
            cache.get(key, lambda: profile)
    ctx = FinanceContext(
        business_id=owner.user_id,
        business_name=owner.business_name,
        db=db,
        settings=get_settings(),
        profile=profile.model_dump() if profile else None,
    )
    await asyncio.to_thread(ctx.ensure_ready)
    return ctx


async def run(fn, *args, **kwargs):
    """Los servicios son síncronos y bloquean (sqlite/Snowflake): se corren en
    un hilo para no congelar el event loop, igual que bcrypt en auth."""
    return await asyncio.to_thread(fn, *args, **kwargs)
