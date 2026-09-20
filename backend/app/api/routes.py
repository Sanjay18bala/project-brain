from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from ..agents.extraction import extract
from ..config import DEFAULT_PROJECT_ID, GITHUB_WEBHOOK_SECRET, SLACK_SIGNING_SECRET
from ..db import get_conn
from ..graph.repository import add_evidence, get_graph, project_exists, upsert_edge, upsert_node
from ..ingestion.github import verify_github_signature
from ..ingestion.slack import verify_slack_signature
from ..security import require_api_key

router = APIRouter()


def _default_project_id() -> uuid.UUID:
    """The single demo project webhook events are written into.

    # ponytail: GitHub/Slack can't set custom headers on their own webhook deliveries,
    # so project_id can't come from a request header (see review finding). PRD scope is
    # a single demo project (multi-project support is P2/stretch), so one configured
    # project id is the right-sized fix. Upgrade path: map GitHub repo full_name / Slack
    # team_id+channel to a project via a lookup table once multi-project support lands.
    """
    if not DEFAULT_PROJECT_ID:
        raise HTTPException(status_code=503, detail="DEFAULT_PROJECT_ID is not configured")
    try:
        return uuid.UUID(DEFAULT_PROJECT_ID)
    except ValueError:
        raise HTTPException(status_code=503, detail="DEFAULT_PROJECT_ID is malformed") from None


def _write_extraction_to_graph(
    conn,
    project_id: uuid.UUID,
    extraction: dict,
    *,
    source_type: str,
    source_ref: str,
    content: str,
    url: str | None,
    occurred_at: datetime,
) -> int:
    node_ids: dict[str, uuid.UUID] = {}
    for entity in extraction["entities"]:
        node_ids[entity["name"]] = upsert_node(conn, project_id, entity["type"], entity["name"])

    for rel in extraction["relationships"]:
        upsert_edge(conn, project_id, node_ids[rel["source"]], node_ids[rel["target"]], rel["relation"])

    for node_id in node_ids.values():
        add_evidence(conn, project_id, node_id, source_type, source_ref, content, url, occurred_at)

    return len(extraction["entities"])


def _process_github_event(project_id: uuid.UUID, payload: dict) -> int:
    """Runs the extraction + DB writes off the event loop (blocking psycopg/openai calls)."""
    extraction = extract(json.dumps(payload))
    subject = payload.get("issue") or payload.get("pull_request") or {}
    source_ref = str(subject.get("number", ""))
    content = json.dumps(payload)[:2000]
    url = payload.get("repository", {}).get("html_url")

    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        return _write_extraction_to_graph(
            conn,
            project_id,
            extraction,
            source_type="github",
            source_ref=source_ref,
            content=content,
            url=url,
            occurred_at=datetime.now(timezone.utc),
        )


def _slack_ts_to_datetime(ts: str | None) -> datetime:
    if not ts:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _process_slack_event(project_id: uuid.UUID, event: dict) -> int:
    """Runs the extraction + DB writes off the event loop, same as GitHub events."""
    text = event["text"][:2000]
    extraction = extract(text)
    content = text
    occurred_at = _slack_ts_to_datetime(event.get("ts"))

    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        return _write_extraction_to_graph(
            conn,
            project_id,
            extraction,
            source_type="slack",
            source_ref=event.get("ts", ""),
            content=content,
            url=None,
            occurred_at=occurred_at,
        )


@router.post("/events/github")
async def receive_github_event(request: Request):
    """No X-API-Key here: the GitHub HMAC signature is the auth boundary for this route —
    GitHub's webhook delivery can't attach custom headers, only the shared webhook secret."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(body, signature, GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="invalid signature")

    project_id = _default_project_id()
    payload = json.loads(body)

    entity_count = await run_in_threadpool(_process_github_event, project_id, payload)
    return {"status": "processed", "entities": entity_count}


@router.post("/events/slack")
async def receive_slack_event(request: Request):
    """No X-API-Key here either: the Slack request signature is the auth boundary, and
    Slack's own url_verification handshake must succeed unauthenticated-by-API-key or the
    Events API subscription can never be activated."""
    body = await request.body()
    if not verify_slack_signature(
        body,
        request.headers.get("X-Slack-Request-Timestamp"),
        request.headers.get("X-Slack-Signature"),
        SLACK_SIGNING_SECRET,
    ):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = json.loads(body)

    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    event = payload.get("event", {})
    if event.get("type") != "message" or event.get("subtype") or event.get("bot_id") or not event.get("text"):
        return {"status": "ignored"}

    project_id = _default_project_id()
    entity_count = await run_in_threadpool(_process_slack_event, project_id, event)
    return {"status": "processed", "entities": entity_count}


@router.get("/projects/{project_id}/graph", dependencies=[Depends(require_api_key)])
def project_graph(project_id: uuid.UUID):
    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        return get_graph(conn, project_id)
