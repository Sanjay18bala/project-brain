import os

os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
os.environ.setdefault("NEBIUS_API_KEY", "x")
os.environ.setdefault("API_KEY", "test-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_preflight_request_is_answered_not_405():
    """The frontend sends X-API-Key, which forces a browser CORS preflight (OPTIONS)
    before every real request. Regression test for the 405 this caused before
    CORSMiddleware was added — a browser client would fail silently on every call."""
    response = client.options(
        "/projects/00000000-0000-0000-0000-000000000001/graph",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-api-key",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
