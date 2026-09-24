"""Slack's OAuth code can't be fabricated any more than a real signed webhook request can
(same limitation documented for test_github_app_connection.py / test_googlechat_connect.py)
— these tests monkeypatch exchange_code_for_team_id to exercise our own routing/callback
logic instead of hitting Slack's real API.
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


def test_install_url_requires_api_key():
    response = client.get("/connections/slack/install", params={"project_id": "00000000-0000-0000-0000-000000000001"})
    assert response.status_code == 401


def test_callback_rejects_malformed_state():
    response = client.get("/connections/slack/callback", params={"code": "abc", "state": "not-a-uuid"})
    assert response.status_code == 400


def test_callback_degrades_gracefully_when_token_exchange_fails(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "project_exists", lambda conn, project_id: True)

    def _raise(code, redirect_uri):
        raise RuntimeError("token exchange failed")

    monkeypatch.setattr(routes, "exchange_code_for_team_id", _raise)

    response = client.get(
        "/connections/slack/callback",
        params={"code": "bad-code", "state": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 502


def test_callback_creates_connection_on_success(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "project_exists", lambda conn, project_id: True)
    monkeypatch.setattr(routes, "exchange_code_for_team_id", lambda code, redirect_uri: "T12345")

    captured = {}

    def fake_create_connection(conn, project_id, platform, external_id):
        captured["project_id"] = project_id
        captured["platform"] = platform
        captured["external_id"] = external_id

    monkeypatch.setattr(routes, "create_connection", fake_create_connection)

    response = client.get(
        "/connections/slack/callback",
        params={"code": "good-code", "state": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "connected", "project_id": "00000000-0000-0000-0000-000000000001"}
    assert captured == {
        "project_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "platform": "slack",
        "external_id": "T12345",
    }


def test_resolve_slack_project_id_uses_connection_mapping(monkeypatch):
    mapped_project = uuid.UUID("00000000-0000-0000-0000-000000000003")
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(
        routes,
        "get_project_id_for_installation",
        lambda conn, external_id, platform: mapped_project if external_id == "T999" else None,
    )

    result = routes._resolve_slack_project_id({"team_id": "T999"})
    assert result == mapped_project


def test_resolve_slack_project_id_is_ignored_when_team_unmapped(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "get_project_id_for_installation", lambda conn, external_id, platform: None)

    result = routes._resolve_slack_project_id({"team_id": "T_UNMAPPED"})
    assert result is None


def test_resolve_slack_project_id_falls_back_to_default_when_no_team_id():
    result = routes._resolve_slack_project_id({})
    assert result == uuid.UUID("00000000-0000-0000-0000-000000000001")
