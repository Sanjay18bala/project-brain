from datetime import datetime, timezone

from app.api.routes import _googlechat_time_to_datetime


def test_parses_rfc3339_with_z_suffix():
    result = _googlechat_time_to_datetime("2026-09-21T12:34:56.789Z")
    assert result == datetime(2026, 9, 21, 12, 34, 56, 789000, tzinfo=timezone.utc)


def test_missing_timestamp_falls_back_to_now():
    before = datetime.now(timezone.utc)
    result = _googlechat_time_to_datetime(None)
    after = datetime.now(timezone.utc)
    assert before <= result <= after


def test_malformed_timestamp_falls_back_to_now():
    before = datetime.now(timezone.utc)
    result = _googlechat_time_to_datetime("not-a-timestamp")
    after = datetime.now(timezone.utc)
    assert before <= result <= after
