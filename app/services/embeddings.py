import asyncio

import httpx

from app.core.config import Settings


class EmbeddingClient:
    """Thin wrapper over the local Ollama embeddings API. Sibling to `LLMClient`
    (`app/services/llm.py`) — the only place that knows the embedding provider.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url
        self._model = settings.ollama_embed_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        semaphore = asyncio.Semaphore(4)

        async def embed_one(client: httpx.AsyncClient, text: str) -> list[float]:
            async with semaphore:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
                response.raise_for_status()
                return response.json()["embedding"]

        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=60.0)) as client:
            return list(await asyncio.gather(*(embed_one(client, text) for text in texts)))
