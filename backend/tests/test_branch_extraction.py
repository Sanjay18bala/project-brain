"""Deterministic (non-LLM) branch tracking from GitHub pull_request payloads
(roadmap-v4 Phase 1) - head.ref/base.ref/default_branch are structural fields GitHub
already sends us, so this is tested by calling _upsert_pr_branches directly with mocked
repository calls, same pattern as the other routes.py helper-function tests.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
os.environ.setdefault("NEBIUS_API_KEY", "x")
os.environ.setdefault("API_KEY", "test-key")

from app.api import routes  # noqa: E402

PR_PAYLOAD = {
    "repository": {"default_branch": "main"},
    "pull_request": {
        "title": "Fix OCR pipeline",
        "head": {"ref": "fix-ocr-pipeline"},
        "base": {"ref": "main"},
    },
}


def test_upserts_head_and_base_branch_nodes_with_correct_default_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(
        routes,
        "upsert_node",
        lambda conn, project_id, type_, name, status="KNOWN", metadata=None: calls.append((type_, name, metadata)) or "node-id",
    )
    monkeypatch.setattr(routes, "find_node_id_by_name", lambda conn, project_id, name: None)

    routes._upsert_pr_branches(conn=None, project_id="p1", payload=PR_PAYLOAD)

    assert ("BRANCH", "fix-ocr-pipeline", {"is_default": False}) in calls
    assert ("BRANCH", "main", {"is_default": True}) in calls


def test_links_pr_to_head_branch_when_pr_node_already_exists(monkeypatch):
    monkeypatch.setattr(routes, "upsert_node", lambda conn, project_id, type_, name, status="KNOWN", metadata=None: "head-node-id")
    monkeypatch.setattr(routes, "find_node_id_by_name", lambda conn, project_id, name: "pr-node-id")

    captured = {}
    monkeypatch.setattr(
        routes,
        "upsert_edge",
        lambda conn, project_id, source_id, target_id, relationship: captured.update(
            source_id=source_id, target_id=target_id, relationship=relationship
        ),
    )

    routes._upsert_pr_branches(conn=None, project_id="p1", payload=PR_PAYLOAD)

    assert captured == {"source_id": "pr-node-id", "target_id": "head-node-id", "relationship": "ON_BRANCH"}


def test_skips_edge_when_no_matching_pr_node_exists_yet(monkeypatch):
    monkeypatch.setattr(routes, "upsert_node", lambda conn, project_id, type_, name, status="KNOWN", metadata=None: "head-node-id")
    monkeypatch.setattr(routes, "find_node_id_by_name", lambda conn, project_id, name: None)

    def fail(*args, **kwargs):
        raise AssertionError("upsert_edge should not be called when no PR node exists yet")

    monkeypatch.setattr(routes, "upsert_edge", fail)

    routes._upsert_pr_branches(conn=None, project_id="p1", payload=PR_PAYLOAD)


def test_ignores_payloads_with_no_pull_request():
    routes._upsert_pr_branches(conn=None, project_id="p1", payload={"issue": {}})
