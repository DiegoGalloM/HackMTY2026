# backend/app/storage/base.py
from abc import ABC, abstractmethod
from typing import Any

from app.models.schemas import BusinessProfile, StoredUser


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


class UserStore(ABC):
    """Store de usuarios, separado de ProfileStore: el perfil de negocio es
    opcional y se llena después del onboarding, mientras que el usuario existe
    desde el registro."""

    @abstractmethod
    async def create_user(self, user: StoredUser) -> bool:
        """True si se creó; False si el username ya estaba tomado.

        Se devuelve un bool en vez de lanzar excepción porque "username ocupado"
        es un caso normal del registro (409), no un error del sistema.
        """

    @abstractmethod
    async def get_user_by_username(self, username: str) -> StoredUser | None: ...
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> StoredUser | None: ...
