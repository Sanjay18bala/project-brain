import hashlib
import hmac

from app.ingestion.slack import verify_slack_signature

SECRET = "test-signing-secret"
NOW = 1_700_000_000.0


def _sign(body: bytes, timestamp: str, secret: str = SECRET) -> str:
    basestring = f"v0:{timestamp}:".encode() + body
    return "v0=" + hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()


def test_valid_recent_signature_is_accepted():
    body = b'{"type":"event_callback"}'
    timestamp = str(int(NOW))
    signature = _sign(body, timestamp)
    assert verify_slack_signature(body, timestamp, signature, SECRET, now=NOW) is True


def test_tampered_body_is_rejected():
    timestamp = str(int(NOW))
    signature = _sign(b'{"type":"event_callback"}', timestamp)
    assert verify_slack_signature(b'{"type":"tampered"}', timestamp, signature, SECRET, now=NOW) is False


def test_stale_timestamp_is_rejected():
    body = b'{"type":"event_callback"}'
    old_timestamp = str(int(NOW) - 600)
    signature = _sign(body, old_timestamp)
    assert verify_slack_signature(body, old_timestamp, signature, SECRET, now=NOW) is False


def test_missing_signature_is_rejected():
    assert verify_slack_signature(b"{}", str(int(NOW)), None, SECRET, now=NOW) is False


def test_missing_secret_is_rejected():
    assert verify_slack_signature(b"{}", str(int(NOW)), "v0=anything", "", now=NOW) is False


def test_non_numeric_timestamp_is_rejected():
    assert verify_slack_signature(b"{}", "not-a-number", "v0=anything", SECRET, now=NOW) is False
