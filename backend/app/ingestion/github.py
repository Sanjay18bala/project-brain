from __future__ import annotations

import hashlib
import hmac


def verify_github_signature(payload_body: bytes, signature_header: str | None, secret: str) -> bool:
    """Verify GitHub's X-Hub-Signature-256 header against the raw request body.

    See TechStack.md §12 — every inbound GitHub webhook must pass this before processing.
    """
    if not signature_header or not secret:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
