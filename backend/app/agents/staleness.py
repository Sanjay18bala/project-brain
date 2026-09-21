from __future__ import annotations

from datetime import datetime


def find_stale_nodes(nodes: list[dict], now: datetime, threshold_days: float) -> list:
    """Returns the ids of nodes that should be marked UNKNOWN: currently KNOWN, with no
    evidence within threshold_days. See PRD.md §7.5.

    CONFLICTED nodes are left alone — a live conflict is a stronger signal than staleness,
    and downgrading it to UNKNOWN would lose that information. A node with no evidence at
    all (last_activity is None) is skipped rather than marked stale — that's "never
    observed", a different thing from "went quiet after being active".
    """
    stale_ids = []
    threshold_seconds = threshold_days * 86400
    for node in nodes:
        if node["status"] != "KNOWN":
            continue
        last_activity = node.get("last_activity")
        if last_activity is None:
            continue
        age_seconds = (now - last_activity).total_seconds()
        if age_seconds > threshold_seconds:
            stale_ids.append(node["id"])
    return stale_ids
