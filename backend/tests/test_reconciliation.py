from datetime import datetime, timedelta, timezone

from app.agents.reconciliation import is_conflicted, rank_claims, recency_score

NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
HALF_LIFE = 3600.0


def test_recency_score_is_1_for_a_claim_from_right_now():
    assert recency_score(NOW, NOW, HALF_LIFE) == 1.0


def test_recency_score_decays_with_age():
    one_half_life_ago = NOW - timedelta(seconds=HALF_LIFE)
    two_half_lives_ago = NOW - timedelta(seconds=2 * HALF_LIFE)
    score_1 = recency_score(one_half_life_ago, NOW, HALF_LIFE)
    score_2 = recency_score(two_half_lives_ago, NOW, HALF_LIFE)
    assert 0 < score_2 < score_1 < 1.0


def test_recency_score_never_negative_for_future_timestamps():
    assert recency_score(NOW + timedelta(hours=1), NOW, HALF_LIFE) == 1.0


def test_rank_claims_sorts_most_recent_first():
    older = {"claimed_state": "IN_PROGRESS", "occurred_at": NOW - timedelta(hours=2)}
    newer = {"claimed_state": "MERGED", "occurred_at": NOW - timedelta(minutes=1)}
    ranked = rank_claims([older, newer], NOW, HALF_LIFE)
    assert ranked[0]["claimed_state"] == "MERGED"
    assert ranked[0]["score"] > ranked[1]["score"]


def test_is_conflicted_true_when_claims_disagree():
    claims = [{"claimed_state": "MERGED"}, {"claimed_state": "IN_PROGRESS"}]
    assert is_conflicted(claims) is True


def test_is_conflicted_false_when_claims_agree():
    claims = [{"claimed_state": "MERGED"}, {"claimed_state": "MERGED"}]
    assert is_conflicted(claims) is False


def test_is_conflicted_false_for_a_single_claim():
    assert is_conflicted([{"claimed_state": "MERGED"}]) is False
