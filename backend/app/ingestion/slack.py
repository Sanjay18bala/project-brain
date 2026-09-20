from __future__ import annotations

import hashlib
import hmac
import time


def verify_slack_signature(
    body: bytes,
    timestamp: str | None,
    signature: str | None,
    secret: str,
    *,
    now: float | None = None,
) -> bool:
    """Verify Slack's X-Slack-Signature header against the raw body and timestamp.

    Rejects requests whose timestamp is more than 5 minutes off, per Slack's own
    replay-protection recommendation. See TechStack.md §11/§12.
    """
    if not timestamp or not signature or not secret:
        return False
    try:
        request_time = int(timestamp)
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - request_time) > 60 * 5:
        return False

    basestring = f"v0:{timestamp}:".encode() + body
    expected = "v0=" + hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
