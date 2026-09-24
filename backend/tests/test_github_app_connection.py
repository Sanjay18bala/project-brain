"""Can't fabricate a real GitHub OAuth `code` any more than we could a Slack/Google
signature — these tests monkeypatch exchange_code_for_token/user_owns_installation to
exercise our own logic (the ownership check that closes the spoofed-installation_id gap),
same limitation documented for test_googlechat_ingestion.py.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
os.environ.setdefault("NEBIUS_API_KEY", "x")
os.environ.setdefault("API_KEY", "test-key")

from contextlib import contextmanager

from fastapi.testclient import TestClient  # noqa: E402

from app.api import routes  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


@contextmanager
def _fake_conn():
    yield None


def test_install_url_requires_api_key():
    response = client.get("/connections/github/install", params={"project_id": "00000000-0000-0000-0000-000000000001"})
    assert response.status_code == 401


def test_callback_rejects_malformed_state():
    response = client.get(
        "/connections/github/callback",
        params={"installation_id": "123", "code": "abc", "state": "not-a-uuid"},
    )
    assert response.status_code == 400


def test_callback_rejects_installation_not_owned_by_authenticated_user(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "project_exists", lambda conn, project_id: True)
    monkeypatch.setattr(routes, "exchange_code_for_token", lambda code: "fake-user-token")
    monkeypatch.setattr(routes, "user_owns_installation", lambda token, installation_id: False)

    response = client.get(
        "/connections/github/callback",
        params={"installation_id": "999999", "code": "abc", "state": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 403


def test_callback_degrades_gracefully_when_token_exchange_fails(monkeypatch):
    monkeypatch.setattr(routes, "get_conn", _fake_conn)
    monkeypatch.setattr(routes, "project_exists", lambda conn, project_id: True)

    def _raise(code):
        raise RuntimeError("token exchange failed")

    monkeypatch.setattr(routes, "exchange_code_for_token", _raise)

    response = client.get(
        "/connections/github/callback",
        params={"installation_id": "999999", "code": "bad-code", "state": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 502
