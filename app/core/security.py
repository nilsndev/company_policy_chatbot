from dataclasses import dataclass

import httpx
from fastapi import Depends, Header, HTTPException

from app.core.config import Settings, get_settings


@dataclass
class CurrentUser:
    id: str
    email: str | None


async def get_current_user(
    authorization: str = Header(default=""),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization[len("bearer "):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_anon_key,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="auth provider unreachable") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    body = response.json()
    return CurrentUser(id=body["id"], email=body.get("email"))
