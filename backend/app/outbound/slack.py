from __future__ import annotations

import httpx

from ..config import SLACK_BOT_TOKEN

SLACK_API_BASE = "https://slack.com/api"


def send_dm(user_id: str, text: str) -> None:
    """Opens (or reuses) a DM channel with a Slack user and posts a message.

    Raises on any failure (missing/invalid SLACK_BOT_TOKEN, Slack API error, network
    issue) — callers decide whether to degrade gracefully. This is the first *outbound*
    Slack call in the codebase; everything before this slice only ever ingested.
    """
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    with httpx.Client(base_url=SLACK_API_BASE, timeout=15.0) as client:
        open_resp = client.post("/conversations.open", headers=headers, json={"users": user_id})
        open_data = open_resp.json()
        if not open_data.get("ok"):
            raise RuntimeError(f"conversations.open failed: {open_data.get('error')}")
        channel_id = open_data["channel"]["id"]

        post_resp = client.post("/chat.postMessage", headers=headers, json={"channel": channel_id, "text": text})
        post_data = post_resp.json()
        if not post_data.get("ok"):
            raise RuntimeError(f"chat.postMessage failed: {post_data.get('error')}")
