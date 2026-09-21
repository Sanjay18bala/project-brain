from __future__ import annotations

BLOCKING_RELATIONSHIPS = {"BLOCKS", "DEPENDS_ON"}


def summarize_node_counts(nodes: list[dict], edges: list[dict]) -> dict:
    """Partitions nodes into exactly one bucket each, priority CONFLICTED > UNKNOWN >
    BLOCKED > ACTIVE — matches PRD.md §10.1's dashboard summary (illustrative counts:
    17 Active, 3 Blocked, 2 Conflicted, 4 Unknown). A node counts as "blocked" if it's the
    target of a BLOCKS/DEPENDS_ON edge, i.e. something else has to finish before it can.
    """
    blocked_target_ids = {edge["target"] for edge in edges if edge["relationship"] in BLOCKING_RELATIONSHIPS}
    counts = {"active": 0, "blocked": 0, "conflicted": 0, "unknown": 0}
    for node in nodes:
        if node["status"] == "CONFLICTED":
            counts["conflicted"] += 1
        elif node["status"] == "UNKNOWN":
            counts["unknown"] += 1
        elif node["id"] in blocked_target_ids:
            counts["blocked"] += 1
        else:
            counts["active"] += 1
    return counts
