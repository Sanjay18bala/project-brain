from __future__ import annotations

import httpx

from ..config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET

GITHUB_API_BASE = "https://api.github.com"


def exchange_code_for_token(code: str) -> str:
    """Exchanges the OAuth `code` from the install callback for a user access token.

    Raises on failure — callers decide how to surface that to the PM's browser.
    """
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET, "code": code},
        )
        data = response.json()
        if "access_token" not in data:
            raise RuntimeError(f"GitHub token exchange failed: {data.get('error_description', data)}")
        return data["access_token"]


def user_owns_installation(user_token: str, installation_id: str) -> bool:
    """Confirms the authenticated user (identified by their own access token) actually has
    the given installation_id in their own installations list.

    This is the check that closes the spoofing gap GitHub's own docs warn about: a bare
    installation_id from the callback query string is not proof of ownership by itself
    (see docs/roadmap-v3-onboarding.md).
    """
    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            f"{GITHUB_API_BASE}/user/installations",
            headers={"Authorization": f"Bearer {user_token}", "Accept": "application/vnd.github+json"},
        )
        data = response.json()
        installations = data.get("installations", [])
        return any(str(installation.get("id")) == str(installation_id) for installation in installations)
