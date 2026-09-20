import hashlib
import hmac

from app.ingestion.github import verify_github_signature


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_is_accepted():
    body = b'{"hello":"world"}'
    secret = "test-secret"
    assert verify_github_signature(body, _sign(body, secret), secret) is True


def test_tampered_body_is_rejected():
    secret = "test-secret"
    signature = _sign(b'{"hello":"world"}', secret)
    assert verify_github_signature(b'{"hello":"tampered"}', signature, secret) is False


def test_missing_signature_is_rejected():
    assert verify_github_signature(b"{}", None, "test-secret") is False


def test_missing_secret_is_rejected():
    assert verify_github_signature(b"{}", "sha256=anything", "") is False
