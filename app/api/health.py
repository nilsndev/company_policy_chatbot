from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.services.neo4j import check_neo4j
from app.services.ollama import check_ollama
from app.services.supabase import check_supabase

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(settings: Settings = Depends(get_settings)) -> dict:
    ollama = await check_ollama(settings)
    neo4j = await check_neo4j(settings)
    supabase = await check_supabase(settings)
    checks = {
        "supabase_reachable": supabase["reachable"],
        "neo4j_reachable": neo4j["reachable"],
        "ollama_reachable": ollama["reachable"],
        "ollama_chat_model_pulled": ollama["chat_model_pulled"],
        "ollama_embed_model_pulled": ollama["embed_model_pulled"],
    }
    return {"status": "ok" if all(checks.values()) else "not_ready", "checks": checks}
