from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(settings: Settings = Depends(get_settings)) -> dict:
    checks = {
        "supabase_url": bool(settings.supabase_url),
        "neo4j_uri": bool(settings.neo4j_uri),
        "ollama_chat_model": bool(settings.ollama_chat_model),
        "ollama_embed_model": bool(settings.ollama_embed_model),
    }
    return {"status": "ok" if all(checks.values()) else "not_ready", "checks": checks}
