from fastapi import APIRouter, Depends, Request

from app.core.security import CurrentUser, get_current_user
from app.models.schemas import PolicyOut
from app.services import db

router = APIRouter(prefix="/api/v1", tags=["policies"])


@router.get("/policies")
async def get_policies(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> list[PolicyOut]:
    rows = await db.list_policies(request.app.state.db_pool)
    return [PolicyOut(**row) for row in rows]
