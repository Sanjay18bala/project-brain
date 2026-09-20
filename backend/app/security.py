from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from .config import API_KEY


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Shared-secret gate for both routes — closes the unauthenticated read/write found in review.

    Not per-user auth (no accounts exist anywhere in this spec); a single API key is the
    smallest thing that stops an unauthenticated caller from reading or writing project data.
    """
    if not API_KEY or not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="invalid API key")
