import httpx

from app.core.config import Settings


async def check_supabase(settings: Settings) -> dict:
    result = {"reachable": False}
    if not (settings.supabase_url and settings.supabase_anon_key):
        return result

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/health",
                headers={"apikey": settings.supabase_anon_key},
            )
            result["reachable"] = response.status_code == 200
    except httpx.HTTPError:
        pass
    return result
