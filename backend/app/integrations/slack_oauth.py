from __future__ import annotations

import httpx

from ..config import SLACK_CLIENT_ID, SLACK_CLIENT_SECRET

SLACK_API_BASE = "https://slack.com/api"


def exchange_code_for_team_id(code: str, redirect_uri: str) -> str:
    """Exchanges the OAuth `code` from the install callback for the authorizing team's id.

    Unlike GitHub's installation_id, this needs no separate ownership check: the code can
    only be redeemed once, for the exact team that completed Slack's consent screen, so the
    team_id in the exchange response IS the proof (see config.py's SLACK_CLIENT_ID comment).
    Raises on failure - callers decide how to surface that to the PM's browser.
    """
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            f"{SLACK_API_BASE}/oauth.v2.access",
            data={
                "client_id": SLACK_CLIENT_ID,
                "client_secret": SLACK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack token exchange failed: {data.get('error')}")
        return data["team"]["id"]
