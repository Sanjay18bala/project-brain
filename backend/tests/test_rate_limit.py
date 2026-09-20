import time

import pytest
from fastapi import HTTPException

from app import security


def _reset():
    security._request_times.clear()


def test_allows_requests_up_to_the_limit():
    _reset()
    for _ in range(security._RATE_LIMIT_MAX_REQUESTS):
        security.enforce_llm_rate_limit()


def test_raises_429_once_limit_exceeded():
    _reset()
    for _ in range(security._RATE_LIMIT_MAX_REQUESTS):
        security.enforce_llm_rate_limit()
    with pytest.raises(HTTPException) as exc_info:
        security.enforce_llm_rate_limit()
    assert exc_info.value.status_code == 429


def test_requests_outside_the_window_are_forgotten(monkeypatch):
    _reset()
    start = time.monotonic()
    monkeypatch.setattr(security.time, "monotonic", lambda: start)
    for _ in range(security._RATE_LIMIT_MAX_REQUESTS):
        security.enforce_llm_rate_limit()

    monkeypatch.setattr(security.time, "monotonic", lambda: start + security._RATE_LIMIT_WINDOW_SECONDS + 1)
    security.enforce_llm_rate_limit()  # does not raise: the old window has fully expired
