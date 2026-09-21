from app.agents.alerts import format_conflict_alert, resolve_slack_recipient


def test_format_conflict_alert_lists_each_claim():
    claims = [
        {"source_type": "github", "claimed_state": "MERGED"},
        {"source_type": "slack", "claimed_state": "IN_PROGRESS"},
    ]
    message = format_conflict_alert("Authentication", claims)
    assert "Authentication" in message
    assert "github: MERGED" in message
    assert "slack: IN_PROGRESS" in message


def test_format_conflict_alert_asks_never_blames():
    message = format_conflict_alert("Authentication", [])
    assert "reconcile" in message.lower()
    assert "fault" not in message.lower()
    assert "blame" not in message.lower()


def test_resolve_slack_recipient_uses_slack_author_directly():
    claim = {"source_type": "slack", "author": "U_ALEX"}
    assert resolve_slack_recipient(claim, {}) == "U_ALEX"


def test_resolve_slack_recipient_maps_github_login_via_identity_links():
    claim = {"source_type": "github", "author": "priya-dev"}
    identity_links = {"priya-dev": "U_PRIYA"}
    assert resolve_slack_recipient(claim, identity_links) == "U_PRIYA"


def test_resolve_slack_recipient_returns_none_for_unmapped_github_login():
    claim = {"source_type": "github", "author": "unknown-dev"}
    assert resolve_slack_recipient(claim, {}) is None


def test_resolve_slack_recipient_returns_none_when_author_missing():
    claim = {"source_type": "slack", "author": None}
    assert resolve_slack_recipient(claim, {}) is None
