"""Replays the planted-event demo scenario from PRD.md §17 against a running backend.

Sends correctly-signed GitHub and Slack webhook events — same signing schemes the real
GitHub/Slack would use — so the extraction/conflict/risk pipeline runs for real, with no
tunnel or registered GitHub/Slack app needed.

Usage:
    cd backend
    .venv/bin/python scripts/demo_events.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

BASE_URL = os.getenv("DEMO_BASE_URL", "http://localhost:8000")
PROJECT_ID = os.getenv("DEFAULT_PROJECT_ID", "00000000-0000-0000-0000-000000000001")
API_KEY = os.environ["API_KEY"]
GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]


def _sign_github(body: bytes) -> str:
    return "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _sign_slack(body: bytes, timestamp: str) -> str:
    basestring = f"v0:{timestamp}:".encode() + body
    return "v0=" + hmac.new(SLACK_SIGNING_SECRET.encode(), basestring, hashlib.sha256).hexdigest()


def send_github_event(client: httpx.Client, payload: dict) -> None:
    body = json.dumps(payload).encode()
    response = client.post(
        "/events/github",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign_github(body)},
    )
    print(f"  -> {response.status_code} {response.json()}")


def send_slack_event(client: httpx.Client, event: dict) -> None:
    payload = {"type": "event_callback", "event": event}
    body = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    response = client.post(
        "/events/slack",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": _sign_slack(body, timestamp),
        },
    )
    print(f"  -> {response.status_code} {response.json()}")


def ask_agent(client: httpx.Client, question: str) -> None:
    response = client.post(
        "/agent/investigate",
        json={"project_id": PROJECT_ID, "question": question},
        headers={"X-API-Key": API_KEY},
    )
    print(f"  Q: {question}")
    print(f"  A: {response.json().get('answer', response.text)}")


def main() -> None:
    repo = {"full_name": "demo/project-brain", "html_url": "https://github.com/demo/project-brain"}

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        print("Step 1 - initial state: GitHub issue for the OCR pipeline")
        send_github_event(
            client,
            {
                "action": "opened",
                "issue": {"number": 1, "title": "OCR Pipeline", "body": "Build the OCR output pipeline."},
                "repository": repo,
            },
        )

        print("Step 2 - Slack: developer switches off OCR")
        send_slack_event(
            client,
            {
                "type": "message",
                "user": "U_ALEX",
                "text": "I'm switching from OCR to database work for now.",
                "channel": "C_GENERAL",
                "ts": str(time.time()),
            },
        )

        print("Step 3 - Slack: dependency appears")
        send_slack_event(
            client,
            {
                "type": "message",
                "user": "U_JORDAN",
                "text": "Frontend integration can't start until the OCR output format is finalized.",
                "channel": "C_GENERAL",
                "ts": str(time.time()),
            },
        )

        print("Step 4 - GitHub: PR provides additional evidence")
        send_github_event(
            client,
            {
                "action": "closed",
                "pull_request": {
                    "number": 12,
                    "title": "Add OCR output schema",
                    "body": "Finalizes the OCR output format.",
                    "merged": True,
                },
                "repository": repo,
            },
        )

        print("Step 5 - conflict: GitHub says authentication merged, Slack disagrees")
        send_github_event(
            client,
            {
                "action": "closed",
                "pull_request": {
                    "number": 13,
                    "title": "Authentication",
                    "body": "Authentication work merged.",
                    "merged": True,
                },
                "repository": repo,
            },
        )
        send_slack_event(
            client,
            {
                "type": "message",
                "user": "U_ALEX",
                "text": "Authentication still needs work, not done yet.",
                "channel": "C_GENERAL",
                "ts": str(time.time()),
            },
        )

        print("\nStep 6 - ask the agent")
        ask_agent(client, "Why might deployment be at risk?")

        print(f"\nDone. Open http://localhost:5173 or query directly, e.g.:")
        print(f"  curl -H 'X-API-Key: {API_KEY}' {BASE_URL}/projects/{PROJECT_ID}/conflicts")


if __name__ == "__main__":
    main()
