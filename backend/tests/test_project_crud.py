import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
os.environ.setdefault("NEBIUS_API_KEY", "x")
os.environ.setdefault("API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_create_project_requires_api_key():
    response = client.post("/projects", json={"name": "Acme Corp"})
    assert response.status_code == 401


def test_create_project_rejects_empty_name():
    response = client.post("/projects", json={"name": ""}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 422


def test_create_project_rejects_oversized_name():
    response = client.post("/projects", json={"name": "x" * 201}, headers={"X-API-Key": "test-key"})
    assert response.status_code == 422


def test_list_projects_requires_api_key():
    response = client.get("/projects")
    assert response.status_code == 401
