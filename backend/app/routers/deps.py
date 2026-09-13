"""
Dependencias compartidas por los routers acotados a un negocio.

`require_owner` vive aquí (y se re-exporta desde business_profile.py) para
que todos los routers `/…/{owner_id}` usen exactamente la misma guardia.
"""

from fastapi import Depends, HTTPException, Path, status

from app.models.schemas import StoredUser
from app.routers.auth import get_current_user


async def require_owner(
    owner_id: str = Path(...),
    current_user: StoredUser = Depends(get_current_user),  # noqa: B008
) -> StoredUser:
    """Los datos de un negocio solo los toca su dueño.

    `owner_id` se declara con `Path(...)` a propósito: sin eso FastAPI lo
    resolvería como query param en cualquier ruta que no tenga un `{owner_id}`
    en su path, y entonces `?owner_id=<el mío>` pasaría el check mientras la
    ruta opera sobre los datos de otro.
    """
    if current_user.user_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden_owner")
    return current_user
