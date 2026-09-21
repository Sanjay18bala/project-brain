from datetime import date

from app.agents.deadlines import find_crossed_deadlines

TODAY = date(2026, 9, 21)

TASK = {"id": "task1", "type": "TASK", "name": "Frontend integration", "status": "KNOWN"}
PAST_DEADLINE = {"id": "d1", "type": "DEADLINE", "name": "2026-09-15", "status": "KNOWN"}
FUTURE_DEADLINE = {"id": "d2", "type": "DEADLINE", "name": "2026-10-01", "status": "KNOWN"}
TODAY_DEADLINE = {"id": "d3", "type": "DEADLINE", "name": "2026-09-21", "status": "KNOWN"}
MALFORMED_DEADLINE = {"id": "d4", "type": "DEADLINE", "name": "soon", "status": "KNOWN"}

DUE_BEFORE_PAST = {"id": "e1", "source": "task1", "target": "d1", "relationship": "DUE_BEFORE", "confidence": 1.0}


def test_flags_a_deadline_in_the_past():
    crossed = find_crossed_deadlines([TASK, PAST_DEADLINE], [DUE_BEFORE_PAST], TODAY)
    assert len(crossed) == 1
    assert crossed[0]["deadline"]["id"] == "d1"
    assert crossed[0]["date"] == "2026-09-15"


def test_includes_the_affected_task():
    crossed = find_crossed_deadlines([TASK, PAST_DEADLINE], [DUE_BEFORE_PAST], TODAY)
    assert [t["id"] for t in crossed[0]["affected_tasks"]] == ["task1"]


def test_leaves_future_deadline_alone():
    crossed = find_crossed_deadlines([FUTURE_DEADLINE], [], TODAY)
    assert crossed == []


def test_today_itself_is_not_yet_crossed():
    crossed = find_crossed_deadlines([TODAY_DEADLINE], [], TODAY)
    assert crossed == []


def test_malformed_date_is_skipped_not_guessed_at():
    crossed = find_crossed_deadlines([MALFORMED_DEADLINE], [], TODAY)
    assert crossed == []


def test_non_deadline_nodes_are_ignored():
    crossed = find_crossed_deadlines([TASK], [], TODAY)
    assert crossed == []


def test_deadline_with_no_affected_tasks_still_reported():
    crossed = find_crossed_deadlines([PAST_DEADLINE], [], TODAY)
    assert len(crossed) == 1
    assert crossed[0]["affected_tasks"] == []
