from app.agents.risk import build_adjacency, detect_risks, downstream_chain

OCR = {"id": "ocr", "type": "TASK", "name": "OCR", "status": "CONFLICTED"}
FRONTEND = {"id": "frontend", "type": "TASK", "name": "Frontend", "status": "KNOWN"}
TESTING = {"id": "testing", "type": "TASK", "name": "Testing", "status": "KNOWN"}
DEPLOYMENT = {"id": "deployment", "type": "TASK", "name": "Deployment", "status": "KNOWN"}
UNRELATED = {"id": "unrelated", "type": "TASK", "name": "Unrelated", "status": "KNOWN"}

CHAIN_EDGES = [
    {"id": "e1", "source": "ocr", "target": "frontend", "relationship": "BLOCKS", "confidence": 1.0},
    {"id": "e2", "source": "frontend", "target": "testing", "relationship": "DEPENDS_ON", "confidence": 1.0},
    {"id": "e3", "source": "testing", "target": "deployment", "relationship": "DUE_BEFORE", "confidence": 1.0},
]


def test_build_adjacency_only_includes_propagating_relationships():
    adjacency = build_adjacency(CHAIN_EDGES)
    assert "ocr" in adjacency
    assert "frontend" in adjacency
    assert "testing" not in adjacency  # DUE_BEFORE doesn't propagate risk


def test_downstream_chain_follows_multiple_hops():
    adjacency = build_adjacency(CHAIN_EDGES)
    chain = downstream_chain("ocr", adjacency)
    targets = [edge["target"] for edge in chain]
    assert targets == ["frontend", "testing"]


def test_downstream_chain_is_cycle_safe():
    cyclic_edges = [
        {"id": "e1", "source": "a", "target": "b", "relationship": "BLOCKS", "confidence": 1.0},
        {"id": "e2", "source": "b", "target": "a", "relationship": "BLOCKS", "confidence": 1.0},
    ]
    adjacency = build_adjacency(cyclic_edges)
    chain = downstream_chain("a", adjacency)
    assert [edge["target"] for edge in chain] == ["b"]


def test_downstream_chain_empty_for_leaf_node():
    adjacency = build_adjacency(CHAIN_EDGES)
    assert downstream_chain("deployment", adjacency) == []


def test_detect_risks_only_flags_conflicted_nodes_with_downstream_impact():
    nodes = [OCR, FRONTEND, TESTING, DEPLOYMENT, UNRELATED]
    risks = detect_risks(nodes, CHAIN_EDGES)
    assert len(risks) == 1
    assert risks[0]["source_node"]["id"] == "ocr"
    assert [step["node"]["id"] for step in risks[0]["chain"]] == ["frontend", "testing"]


def test_detect_risks_ignores_conflicted_node_with_no_downstream():
    nodes = [{**OCR, "id": "isolated"}, FRONTEND]
    risks = detect_risks(nodes, CHAIN_EDGES)
    assert risks == []


def test_detect_risks_empty_when_nothing_conflicted():
    nodes = [FRONTEND, TESTING, DEPLOYMENT]
    assert detect_risks(nodes, CHAIN_EDGES) == []
