# backend/app/storage/base.py
from abc import ABC, abstractmethod
from typing import Any

from app.models.schemas import BusinessProfile


class ProfileStore(ABC):
    @abstractmethod
    async def save_profile(self, owner_id: str, profile: BusinessProfile) -> None: ...
    @abstractmethod
    async def get_profile(self, owner_id: str) -> BusinessProfile | None: ...
    @abstractmethod
    async def list_profiles(self, category: str | None = None) -> list[BusinessProfile]: ...
    @abstractmethod
    async def category_stats(self, category: str) -> dict[str, Any]:
        """% de negocios que respondieron True a cada pregunta, por categoría —
        esto es lo que alimenta el futuro modelo de sugerencia de inventario."""