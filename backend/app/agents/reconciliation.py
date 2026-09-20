from __future__ import annotations

import math
from datetime import datetime

DEFAULT_HALF_LIFE_SECONDS = 24 * 60 * 60


def recency_score(occurred_at: datetime, now: datetime, half_life_seconds: float = DEFAULT_HALF_LIFE_SECONDS) -> float:
    """exp(-age / half_life) — see TechStack.md §4a. A brand-new claim scores near 1.0."""
    age_seconds = max((now - occurred_at).total_seconds(), 0.0)
    return math.exp(-age_seconds / half_life_seconds)


def rank_claims(claims: list[dict], now: datetime, half_life_seconds: float = DEFAULT_HALF_LIFE_SECONDS) -> list[dict]:
    """Attach a recency score to each claim, most recent first. Never picks a winner —
    per PRD.md §7.4, conflicting claims stay CONFLICTED until a human confirms one."""
    scored = [{**claim, "score": recency_score(claim["occurred_at"], now, half_life_seconds)} for claim in claims]
    return sorted(scored, key=lambda c: c["score"], reverse=True)


def is_conflicted(claims: list[dict]) -> bool:
    """True if the claims disagree on claimed_state."""
    return len({claim["claimed_state"] for claim in claims}) > 1
