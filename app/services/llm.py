import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import Settings


class LLMClient:
    """Thin wrapper over the local Ollama chat API. Routers/services never
    call Ollama directly — this is the only place that knows the provider.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url
        self._model = settings.ollama_chat_model

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        payload = {"model": self._model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, read=120.0)) as client:
            async with client.stream(
                "POST", f"{self._base_url}/api/chat", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if chunk.get("done"):
                        break
                    text = chunk.get("message", {}).get("content", "")
                    if text:
                        yield text
