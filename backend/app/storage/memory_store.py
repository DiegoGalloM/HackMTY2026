from collections import defaultdict
from typing import Any

from app.models.schemas import BusinessProfile
from app.storage.base import ProfileStore


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

        totals: dict[str, int] = defaultdict(int)
        for p in profiles:
            for key, value in p.answers.items():
                if value:
                    totals[key] += 1

        n = len(profiles)
        return {
            "category": category,
            "n_negocios": n,
            "answers_pct_true": {k: round(v / n, 2) for k, v in totals.items()},
        }