"""Thin httpx wrapper over Supabase Storage REST, service_role only.

Matches the existing lightweight-httpx-client style (`supabase.py`, `ollama.py`)
rather than adding the `supabase-py` SDK as a dependency.
"""

import httpx

from app.core.config import Settings

BUCKET = "policy-docs"


def _headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


async def ensure_bucket(settings: Settings) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{settings.supabase_url}/storage/v1/bucket",
            headers=_headers(settings),
            json={"id": BUCKET, "name": BUCKET, "public": False},
        )
        if response.status_code not in (200, 201) and "already exists" not in response.text:
            response.raise_for_status()


async def upload_object(settings: Settings, path: str, data: bytes) -> None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{settings.supabase_url}/storage/v1/object/{BUCKET}/{path}",
            headers={**_headers(settings), "Content-Type": "text/markdown", "x-upsert": "true"},
            content=data,
        )
        response.raise_for_status()


async def download_object(settings: Settings, path: str) -> bytes:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{settings.supabase_url}/storage/v1/object/{BUCKET}/{path}",
            headers=_headers(settings),
        )
        response.raise_for_status()
        return response.content
