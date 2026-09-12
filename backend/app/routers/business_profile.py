# backend/app/routers/business_profile.py
from fastapi import APIRouter
from app.models.schemas import BusinessProfile

router = APIRouter(prefix="/business-profile", tags=["business-profile"])
_profiles: dict[str, BusinessProfile] = {}

@router.post("/{owner_id}")
async def save_profile(owner_id: str, profile: BusinessProfile):
    _profiles[owner_id] = profile
    return {"status": "ok"}

@router.get("/{owner_id}")
async def get_profile(owner_id: str):
    return _profiles.get(owner_id)