import logging

from fastapi import APIRouter, Depends, Request

from app.core.security import CurrentUser, get_current_user
from app.models.schemas import ProfileIn, ProfileOut
from app.services import db
from app.services import neo4j as neo4j_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["profile"])


@router.get("/profile")
async def get_profile(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> ProfileOut:
    profile = await db.get_profile(request.app.state.db_pool, user.id)
    return ProfileOut(
        id=user.id,
        department=profile["department"] if profile else None,
        role=profile["role"] if profile else None,
    )


@router.post("/profile")
async def set_profile(
    body: ProfileIn, request: Request, user: CurrentUser = Depends(get_current_user)
) -> ProfileOut:
    saved = await db.upsert_profile(request.app.state.db_pool, user.id, body.department, body.role)
    try:
        await neo4j_service.upsert_employee(
            request.app.state.neo4j_driver, user.id, saved["department"], saved["role"]
        )
    except Exception:
        # Best-effort: don't fail the profile save over a graph hiccup. RBAC
        # enforcement (M4) isn't wired to retrieval yet; `scripts/seed_graph.py`
        # can also backfill Employee nodes if this write is missed.
        logger.warning("failed to sync employee to Neo4j graph for user %s", user.id, exc_info=True)
    return ProfileOut(id=user.id, department=saved["department"], role=saved["role"])
