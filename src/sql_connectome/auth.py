import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings


def require_bearer(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="BEARER_REQUIRED")

    presented = authorization.removeprefix("Bearer ").strip()
    expected = settings.api_token.get_secret_value()
    if not presented or not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="INVALID_TOKEN")
