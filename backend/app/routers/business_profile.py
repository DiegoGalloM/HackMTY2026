from fastapi import APIRouter, Depends

from app.models.schemas import BusinessProfile
from app.storage import get_store
from app.storage.base import ProfileStore

router = APIRouter(prefix="/business-profile", tags=["business-profile"])


@router.post("/{owner_id}")
async def save_profile(
    owner_id: str,
    profile: BusinessProfile,
    store: ProfileStore = Depends(get_store),
):
    await store.save_profile(owner_id, profile)
    return {"status": "ok"}


@router.get("/{owner_id}")
async def get_profile(owner_id: str, store: ProfileStore = Depends(get_store)):
    return await store.get_profile(owner_id)


@router.get("/stats/{category}")
async def get_category_stats(category: str, store: ProfileStore = Depends(get_store)):
    return await store.category_stats(category)