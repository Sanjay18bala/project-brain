from app.agents.dashboard import summarize_node_counts

ACTIVE_NODE = {"id": "n1", "status": "KNOWN"}
CONFLICTED_NODE = {"id": "n2", "status": "CONFLICTED"}
UNKNOWN_NODE = {"id": "n3", "status": "UNKNOWN"}
BLOCKED_NODE = {"id": "n4", "status": "KNOWN"}

BLOCKS_EDGE = {"id": "e1", "source": "n1", "target": "n4", "relationship": "BLOCKS"}


def test_counts_each_status_bucket():
    counts = summarize_node_counts([ACTIVE_NODE, CONFLICTED_NODE, UNKNOWN_NODE, BLOCKED_NODE], [BLOCKS_EDGE])
    assert counts == {"active": 1, "blocked": 1, "conflicted": 1, "unknown": 1}


def test_conflicted_takes_priority_over_blocked():
    # n2 is CONFLICTED but also the target of a BLOCKS edge - should count as conflicted only
    edge = {"id": "e2", "source": "n1", "target": "n2", "relationship": "BLOCKS"}
    counts = summarize_node_counts([CONFLICTED_NODE], [edge])
    assert counts == {"active": 0, "blocked": 0, "conflicted": 1, "unknown": 0}


def test_unknown_takes_priority_over_blocked():
    edge = {"id": "e3", "source": "n1", "target": "n3", "relationship": "DEPENDS_ON"}
    counts = summarize_node_counts([UNKNOWN_NODE], [edge])
    assert counts == {"active": 0, "blocked": 0, "conflicted": 0, "unknown": 1}


def test_non_blocking_relationship_does_not_count_as_blocked():
    edge = {"id": "e4", "source": "n1", "target": "n4", "relationship": "RELATED_TO"}
    counts = summarize_node_counts([BLOCKED_NODE], [edge])
    assert counts == {"active": 1, "blocked": 0, "conflicted": 0, "unknown": 0}


def test_empty_graph_is_all_zero():
    assert summarize_node_counts([], []) == {"active": 0, "blocked": 0, "conflicted": 0, "unknown": 0}
