"""Google Chat has no OAuth-install redirect we control (the PM adds the bot to a space
through Google's own UI), so the connect flow runs the other way: a short code from our
authenticated API, typed into the space, matched in the webhook handler. These tests
monkeypatch the repository layer (same pattern as test_github_app_connection.py) rather
than hitting a real database.
"""

import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
os.environ.setdefault("NEBIUS_API_KEY", "x")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("DEFAULT_PROJECT_ID", "00000000-0000-0000-0000-000000000001")

from contextlib import contextmanager

from fastapi.testclient import TestClient  # noqa: E402

from app.api import routes  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


@contextmanager
def _fake_conn():
    yield None


def test_connect_code_requires_api_key():
    response = client.post(
        "/connections/googlechat/code", params={"project_id": "00000000-0000-0000-0000-000000000001"}
    )
    assert response.status_code == 401


def test_connect_code_rejects_unknown_project(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "project_exists", lambda conn, project_id: False)

    response = client.post(
        "/connections/googlechat/code",
        params={"project_id": "00000000-0000-0000-0000-000000000001"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 404


def test_connect_code_returns_generated_code(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "project_exists", lambda conn, project_id: True)
    monkeypatch.setattr(routes, "create_connect_code", lambda conn, project_id, platform: "deadbeef")

    response = client.post(
        "/connections/googlechat/code",
        params={"project_id": "00000000-0000-0000-0000-000000000001"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    assert response.json() == {"code": "deadbeef"}


def test_try_consume_connect_code_matches_and_lowercases(monkeypatch):
    captured = {}

    def fake_consume(conn, code, platform):
        captured["code"] = code
        captured["platform"] = platform
        return uuid.UUID("00000000-0000-0000-0000-000000000002")

    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "consume_connect_code", fake_consume)

    result = routes._try_consume_connect_code("connect DEADBEEF")
    assert result == uuid.UUID("00000000-0000-0000-0000-000000000002")
    assert captured == {"code": "deadbeef", "platform": "googlechat"}


def test_try_consume_connect_code_rejects_non_matching_text(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("consume_connect_code should not be called for non-matching text")

    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "consume_connect_code", fail)

    assert routes._try_consume_connect_code("hello there") is None


def test_resolve_googlechat_project_id_uses_connection_mapping(monkeypatch):
    mapped_project = uuid.UUID("00000000-0000-0000-0000-000000000003")
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(
        routes,
        "get_project_id_for_installation",
        lambda conn, external_id, platform: mapped_project if external_id == "spaces/AAA" else None,
    )

    result = routes._resolve_googlechat_project_id({"space": {"name": "spaces/AAA"}})
    assert result == mapped_project


def test_resolve_googlechat_project_id_falls_back_to_default_when_unmapped(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "get_project_id_for_installation", lambda conn, external_id, platform: None)

    result = routes._resolve_googlechat_project_id({"space": {"name": "spaces/UNMAPPED"}})
    assert result == uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_resolve_googlechat_project_id_falls_back_to_default_when_no_space():
    result = routes._resolve_googlechat_project_id({})
    assert result == uuid.UUID("00000000-0000-0000-0000-000000000001")
