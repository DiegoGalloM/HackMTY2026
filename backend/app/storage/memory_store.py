from collections import defaultdict
from typing import Any

from app.models.schemas import BusinessProfile, StoredUser
from app.storage.base import ProfileStore, UserStore


class MemoryProfileStore(ProfileStore):
    def __init__(self):
        self._profiles: dict[str, BusinessProfile] = {}

    async def save_profile(self, owner_id: str, profile: BusinessProfile) -> None:
        self._profiles[owner_id] = profile

    async def get_profile(self, owner_id: str) -> BusinessProfile | None:
        return self._profiles.get(owner_id)

    async def list_profiles(self, category: str | None = None) -> list[BusinessProfile]:
        profiles = list(self._profiles.values())
        if category:
            profiles = [p for p in profiles if p.category == category]
        return profiles

    async def category_stats(self, category: str) -> dict[str, Any]:
        profiles = await self.list_profiles(category)
        if not profiles:
            return {"category": category, "n_negocios": 0, "answers_pct_true": {}}

        # Se cuentan todas las preguntas que aparecen en la categoría, incluso las
        # que siempre salieron False (quedan en 0.0). SnowflakeProfileStore hace lo
        # mismo con FLATTEN — las dos implementaciones tienen que devolver la misma
        # forma, porque /business-profile/stats/{category} no sabe cuál está activa.
        totals: dict[str, int] = defaultdict(int)
        for p in profiles:
            for key, value in p.answers.items():
                totals[key] += 1 if value else 0

        n = len(profiles)
        return {
            "category": category,
            "n_negocios": n,
            "answers_pct_true": {k: round(v / n, 2) for k, v in totals.items()},
        }


class MemoryUserStore(UserStore):
    def __init__(self):
        # Dos índices porque las dos búsquedas son igual de frecuentes: por
        # username en el login y por user_id al validar el token de cada request.
        self._by_username: dict[str, StoredUser] = {}
        self._by_id: dict[str, StoredUser] = {}

    async def create_user(self, user: StoredUser) -> bool:
        key = user.username.strip().lower()
        if key in self._by_username:
            return False
        self._by_username[key] = user
        self._by_id[user.user_id] = user
        return True

    async def get_user_by_username(self, username: str) -> StoredUser | None:
        return self._by_username.get(username.strip().lower())

    async def get_user_by_id(self, user_id: str) -> StoredUser | None:
        return self._by_id.get(user_id)
