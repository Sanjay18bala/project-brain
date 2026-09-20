from app.api.routes import _classify_github_event_type


def test_classifies_pull_request_events():
    assert _classify_github_event_type({"pull_request": {}}) == "pull_request"


def test_classifies_issue_events():
    assert _classify_github_event_type({"issue": {}}) == "issue"


def test_classifies_push_events():
    assert _classify_github_event_type({"commits": []}) == "push"


def test_classifies_unrecognized_payloads_as_unknown():
    assert _classify_github_event_type({"ref": "refs/heads/main"}) == "unknown"


def test_pull_request_key_takes_precedence_when_both_are_present():
    assert _classify_github_event_type({"pull_request": {}, "issue": {}}) == "pull_request"
