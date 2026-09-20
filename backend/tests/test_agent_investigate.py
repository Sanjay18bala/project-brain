import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
os.environ.setdefault("NEBIUS_API_KEY", "x")
os.environ.setdefault("API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)
PROJECT_ID = "00000000-0000-0000-0000-000000000001"


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
