from __future__ import annotations

from collections import deque

PROPAGATING_RELATIONSHIPS = {"BLOCKS", "DEPENDS_ON"}


def build_adjacency(edges: list[dict]) -> dict[str, list[dict]]:
    """Maps each node id to the edges that propagate risk downstream from it.

    # ponytail: treats BLOCKS and DEPENDS_ON as propagating in the same source->target
    # direction, matching PRD.md §7.1's diagram (arrows flow downstream regardless of
    # the specific relation label). A stricter model would distinguish "X blocks Y" from
    # "X depends on Y" (opposite real-world causality); revisit if that distinction
    # actually matters for the demo.
    """
    adjacency: dict[str, list[dict]] = {}
    for edge in edges:
        if edge["relationship"] not in PROPAGATING_RELATIONSHIPS:
            continue
        adjacency.setdefault(edge["source"], []).append(edge)
    return adjacency


def downstream_chain(start_node_id: str, adjacency: dict[str, list[dict]]) -> list[dict]:
    """BFS from start_node_id along propagating edges; each reachable node appears once,
    via the first edge that reached it. Cycle-safe."""
    visited = {start_node_id}
    chain: list[dict] = []
    queue = deque(adjacency.get(start_node_id, []))
    while queue:
        edge = queue.popleft()
        target = edge["target"]
        if target in visited:
            continue
        visited.add(target)
        chain.append(edge)
        queue.extend(adjacency.get(target, []))
    return chain


def detect_risks(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """A CONFLICTED node's uncertainty is a *potential* risk to anything downstream of it
    via BLOCKS/DEPENDS_ON — distinguished from a confirmed failure, which this system
    never asserts (PRD.md §7.7). Nodes with no downstream dependents produce no risk."""
    adjacency = build_adjacency(edges)
    nodes_by_id = {n["id"]: n for n in nodes}

    risks = []
    for node in nodes:
        if node["status"] != "CONFLICTED":
            continue
        chain = downstream_chain(node["id"], adjacency)
        if not chain:
            continue
        risks.append(
            {
                "source_node": node,
                "chain": [{"edge": edge, "node": nodes_by_id.get(edge["target"])} for edge in chain],
            }
        )
    return risks
