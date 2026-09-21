from __future__ import annotations

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from ..config import GOOGLE_CHAT_AUDIENCE

CHAT_ISSUER_EMAIL = "chat@system.gserviceaccount.com"


def verify_google_chat_request(bearer_token: str | None) -> bool:
    """Verifies a Google Chat HTTP endpoint request's bearer token.

    Unlike GitHub's HMAC or Slack's v0= signing, this isn't a shared secret checkable
    offline — Google Chat sends a Google-signed OIDC ID token, and verification calls out
    to Google's public key infrastructure via the google-auth library. See
    https://developers.google.com/workspace/chat/verify-requests-from-chat.
    """
    if not bearer_token or not GOOGLE_CHAT_AUDIENCE:
        return False
    try:
        token = id_token.verify_oauth2_token(bearer_token, google_requests.Request(), GOOGLE_CHAT_AUDIENCE)
    except Exception:
        return False
    return token.get("email") == CHAT_ISSUER_EMAIL
