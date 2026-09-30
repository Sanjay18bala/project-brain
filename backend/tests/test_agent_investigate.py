import json
import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
os.environ.setdefault("NEBIUS_API_KEY", "x")
os.environ.setdefault("API_KEY", "test-key")

from contextlib import contextmanager

from fastapi.testclient import TestClient  # noqa: E402

from app.api import routes  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
PROJECT_ID = "00000000-0000-0000-0000-000000000001"


@contextmanager
def _fake_conn():
    yield None


def test_investigate_requires_api_key():
    response = client.post("/agent/investigate", json={"project_id": PROJECT_ID, "question": "why?"})
    assert response.status_code == 401


def test_investigate_rejects_empty_question():
    response = client.post(
        "/agent/investigate",
        json={"project_id": PROJECT_ID, "question": ""},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 422


def test_investigate_rejects_oversized_question():
    response = client.post(
        "/agent/investigate",
        json={"project_id": PROJECT_ID, "question": "x" * 501},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 422


def test_investigate_rejects_malformed_project_id():
    response = client.post(
        "/agent/investigate",
        json={"project_id": "not-a-uuid", "question": "why?"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 422


def test_investigate_returns_sources_without_leaking_raw_content(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "project_exists", lambda conn, project_id: True)
    monkeypatch.setattr(routes, "get_graph", lambda conn, project_id: {"nodes": [], "edges": []})
    monkeypatch.setattr(routes, "_compute_conflicts", lambda conn, project_id: [])

    evidence_row = {
        "id": "ev-1",
        "node_name": "Login page",
        "source_type": "slack",
        "source_ref": "123.456",
        "content": "secret internal detail that must not leak",
        "url": None,
        "occurred_at": "2026-09-24T00:00:00Z",
        "author": "alex",
    }
    monkeypatch.setattr(routes, "_gather_evidence", lambda conn, project_id, question: ([evidence_row], False))
    monkeypatch.setattr(routes, "answer_question", lambda question, context: "The login page is blocked.")

    response = client.post(
        "/agent/investigate",
        json={"project_id": PROJECT_ID, "question": "what's blocked?"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The login page is blocked."
    assert body["sources"] == [
        {"node_name": "Login page", "source_type": "slack", "occurred_at": "2026-09-24T00:00:00Z", "url": None}
    ]
    assert "secret internal detail" not in json.dumps(body)


def test_dedupe_sources_drops_duplicates_of_the_same_node():
    evidence = [
        {"node_name": "repo", "source_type": "github", "occurred_at": f"t{i}", "url": "u", "content": "x"}
        for i in range(10)
    ]

    sources = routes._dedupe_sources(evidence)

    assert sources == [{"node_name": "repo", "source_type": "github", "occurred_at": "t0", "url": "u"}]


def test_dedupe_sources_caps_the_number_of_distinct_sources():
    evidence = [
        {"node_name": f"node-{i}", "source_type": "github", "occurred_at": f"t{i}", "url": "u", "content": "x"}
        for i in range(10)
    ]

    sources = routes._dedupe_sources(evidence)

    assert len(sources) == routes._MAX_RETURNED_SOURCES
