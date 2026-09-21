from datetime import datetime, timedelta, timezone

from app.agents.staleness import find_stale_nodes

NOW = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
THRESHOLD_DAYS = 3.0


def test_marks_known_node_stale_past_threshold():
    nodes = [{"id": "n1", "status": "KNOWN", "last_activity": NOW - timedelta(days=4)}]
    assert find_stale_nodes(nodes, NOW, THRESHOLD_DAYS) == ["n1"]


def test_leaves_recently_active_known_node_alone():
    nodes = [{"id": "n1", "status": "KNOWN", "last_activity": NOW - timedelta(days=1)}]
    assert find_stale_nodes(nodes, NOW, THRESHOLD_DAYS) == []


def test_never_downgrades_a_conflicted_node():
    nodes = [{"id": "n1", "status": "CONFLICTED", "last_activity": NOW - timedelta(days=30)}]
    assert find_stale_nodes(nodes, NOW, THRESHOLD_DAYS) == []


def test_already_unknown_node_is_not_touched_again():
    nodes = [{"id": "n1", "status": "UNKNOWN", "last_activity": NOW - timedelta(days=30)}]
    assert find_stale_nodes(nodes, NOW, THRESHOLD_DAYS) == []


def test_node_with_no_evidence_at_all_is_not_marked_stale():
    nodes = [{"id": "n1", "status": "KNOWN", "last_activity": None}]
    assert find_stale_nodes(nodes, NOW, THRESHOLD_DAYS) == []


def test_exactly_at_threshold_is_not_yet_stale():
    nodes = [{"id": "n1", "status": "KNOWN", "last_activity": NOW - timedelta(days=THRESHOLD_DAYS)}]
    assert find_stale_nodes(nodes, NOW, THRESHOLD_DAYS) == []
