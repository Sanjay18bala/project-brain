from __future__ import annotations

from datetime import date, datetime


def _parse_deadline_date(name: str) -> date | None:
    try:
        return datetime.strptime(name.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def find_crossed_deadlines(nodes: list[dict], edges: list[dict], today: date) -> list[dict]:
    """DEADLINE nodes whose date has passed, with the tasks that were DUE_BEFORE them.

    A DEADLINE node whose name isn't a parseable YYYY-MM-DD date is skipped, not guessed
    at — matches PRD.md §6 "unknown is a valid state" over inventing certainty. This never
    touches node.status; deadline compliance and epistemic confidence
    (KNOWN/CONFLICTED/UNKNOWN) are different axes.
    """
    nodes_by_id = {n["id"]: n for n in nodes}
    deadline_ids = {n["id"] for n in nodes if n["type"] == "DEADLINE"}

    affected: dict = {}
    for edge in edges:
        if edge["relationship"] == "DUE_BEFORE" and edge["target"] in deadline_ids:
            affected.setdefault(edge["target"], []).append(nodes_by_id.get(edge["source"]))

    crossed = []
    for node in nodes:
        if node["type"] != "DEADLINE":
            continue
        parsed = _parse_deadline_date(node["name"])
        if parsed is None or parsed >= today:
            continue
        crossed.append(
            {
                "deadline": node,
                "date": parsed.isoformat(),
                "affected_tasks": [t for t in affected.get(node["id"], []) if t is not None],
            }
        )
    return crossed
