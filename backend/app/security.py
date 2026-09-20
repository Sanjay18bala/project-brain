from __future__ import annotations

import hmac
import threading
import time
from collections import deque

from fastapi import Header, HTTPException

from .config import API_KEY


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Shared-secret gate for both routes — closes the unauthenticated read/write found in review.

    Not per-user auth (no accounts exist anywhere in this spec); a single API key is the
    smallest thing that stops an unauthenticated caller from reading or writing project data.
    """
    if not API_KEY or not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="invalid API key")


_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 10
_request_times: deque[float] = deque()
_rate_limit_lock = threading.Lock()


def enforce_llm_rate_limit() -> None:
    """Naive in-process sliding-window limiter for routes with real per-call LLM billing cost.

    Only one API key exists (see require_api_key), so a per-key limit is effectively global —
    that's fine here, it's meant to bound cost from a leaked key, not to be a fairness scheme.

    # ponytail: single-process, in-memory; move to Redis/a shared store if this ever runs as
    # more than one instance, or if per-key (not global) limits start to matter.
    """
    now = time.monotonic()
    with _rate_limit_lock:
        while _request_times and now - _request_times[0] > _RATE_LIMIT_WINDOW_SECONDS:
            _request_times.popleft()
        if len(_request_times) >= _RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(status_code=429, detail="rate limit exceeded, try again shortly")
        _request_times.append(now)
