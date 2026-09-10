import httpx

from app.core.config import Settings


async def check_ollama(settings: Settings) -> dict:
    result = {"reachable": False, "chat_model_pulled": False, "embed_model_pulled": False}
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
    except httpx.HTTPError:
        return result

    result["reachable"] = True
    pulled = {model.get("model") or model.get("name") for model in response.json().get("models", [])}
    result["chat_model_pulled"] = settings.ollama_chat_model in pulled
    result["embed_model_pulled"] = settings.ollama_embed_model in pulled
    return result
