from app.api import routes


class _FakeConn:
    pass


def test_gather_evidence_dedupes_rows_present_in_both_semantic_and_recent(monkeypatch):
    semantic_rows = [{"id": "e1", "content": "a"}, {"id": "e2", "content": "b"}]
    recent_rows = [{"id": "e2", "content": "b"}, {"id": "e3", "content": "c"}]

    monkeypatch.setattr(routes, "embed_text", lambda text: [0.1, 0.2])
    monkeypatch.setattr(routes, "search_evidence_by_similarity", lambda conn, project_id, emb, limit: semantic_rows)
    monkeypatch.setattr(routes, "get_evidence_for_project", lambda conn, project_id, limit: recent_rows)

    combined, truncated = routes._gather_evidence(_FakeConn(), "project-id", "why is this blocked?")

    assert [row["id"] for row in combined] == ["e1", "e2", "e3"]
    assert truncated is False


def test_gather_evidence_degrades_to_recency_only_when_embedding_fails(monkeypatch):
    recent_rows = [{"id": "e1", "content": "a"}]

    def _raise(text):
        raise RuntimeError("embedding service down")

    monkeypatch.setattr(routes, "embed_text", _raise)
    monkeypatch.setattr(routes, "get_evidence_for_project", lambda conn, project_id, limit: recent_rows)

    combined, truncated = routes._gather_evidence(_FakeConn(), "project-id", "why is this blocked?")

    assert combined == recent_rows
    assert truncated is False


def test_gather_evidence_flags_truncation_when_recent_window_is_full(monkeypatch):
    full_recent = [{"id": f"e{i}", "content": "x"} for i in range(routes._RECENT_EVIDENCE_LIMIT)]

    monkeypatch.setattr(routes, "embed_text", lambda text: [0.1])
    monkeypatch.setattr(routes, "search_evidence_by_similarity", lambda conn, project_id, emb, limit: [])
    monkeypatch.setattr(routes, "get_evidence_for_project", lambda conn, project_id, limit: full_recent)

    _combined, truncated = routes._gather_evidence(_FakeConn(), "project-id", "what changed?")

    assert truncated is True
