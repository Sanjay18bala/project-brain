from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

from ..agents.alerts import format_conflict_alert, resolve_slack_recipient
from ..agents.dashboard import summarize_node_counts
from ..agents.deadlines import find_crossed_deadlines
from ..agents.embeddings import embed_text
from ..agents.extraction import extract
from ..agents.investigation import answer_question
from ..agents.reconciliation import is_conflicted, rank_claims
from ..agents.risk import detect_risks
from ..agents.staleness import find_stale_nodes
from ..config import (
    DEFAULT_PROJECT_ID,
    GITHUB_WEBHOOK_SECRET,
    RECENCY_HALF_LIFE_SECONDS,
    SLACK_SIGNING_SECRET,
    STALENESS_THRESHOLD_DAYS,
)
from ..db import get_conn
from ..graph.repository import (
    add_evidence,
    add_state_change,
    get_conflicted_nodes,
    get_evidence_for_project,
    get_graph,
    get_identity_links,
    get_node_last_activity,
    get_state_changes_for_node,
    has_action_been_taken,
    lock_node,
    log_event,
    mark_nodes_unknown,
    project_exists,
    record_action,
    search_evidence_by_similarity,
    set_node_status,
    upsert_edge,
    upsert_node,
)
from ..ingestion.github import verify_github_signature
from ..ingestion.slack import verify_slack_signature
from ..outbound.slack import send_dm
from ..security import enforce_llm_rate_limit, require_api_key

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
    author: str | None = None,
) -> int:
    node_ids: dict[str, uuid.UUID] = {}
    for entity in extraction["entities"]:
        node_ids[entity["name"]] = upsert_node(conn, project_id, entity["type"], entity["name"])

    for rel in extraction["relationships"]:
        upsert_edge(conn, project_id, node_ids[rel["source"]], node_ids[rel["target"]], rel["relation"])

    for change in extraction["state_changes"]:
        node_id = node_ids[change["entity"]]
        add_state_change(
            conn, project_id, node_id, source_type, source_ref, change["new_state"], change["confidence"], occurred_at, author=author
        )

    embedding = None
    if node_ids:
        try:
            embedding = embed_text(content)
        except Exception:
            embedding = None  # evidence is still stored; just not semantically searchable this time

    for node_id in node_ids.values():
        add_evidence(conn, project_id, node_id, source_type, source_ref, content, url, occurred_at, author=author, embedding=embedding)

    # Recompute conflict status for every touched node from its full claim history —
    # never derived from just this event, so a past conflict stays CONFLICTED until
    # actual agreeing/superseding evidence arrives (PRD.md §7.4: never silently resolved).
    # lock_node serializes this against a concurrent GitHub+Slack write racing on the same
    # node — without it, two overlapping transactions can each miss the other's just-
    # inserted claim and both write KNOWN, silently swallowing the exact conflict this
    # feature exists to catch.
    for node_name, node_id in node_ids.items():
        lock_node(conn, node_id)
        claims = get_state_changes_for_node(conn, node_id)
        newly_conflicted = is_conflicted(claims)
        set_node_status(conn, node_id, "CONFLICTED" if newly_conflicted else "KNOWN")
        if newly_conflicted:
            _send_conflict_alerts(conn, project_id, node_id, node_name, claims)

    return len(extraction["entities"])


def _send_conflict_alerts(conn, project_id: uuid.UUID, node_id: uuid.UUID, node_name: str, claims: list[dict]) -> None:
    """Best-effort: DMs each party to a conflict once ever per (node, recipient) — the
    actions table's UNIQUE constraint backs this even under a race. A Slack failure (no
    SLACK_BOT_TOKEN configured, network issue, etc.) is swallowed — an alert is a nice-to-
    have on top of the conflict already being visible via GET /projects/{id}/conflicts and
    the agent chat, never a hard requirement for event processing to succeed.
    """
    identity_links = get_identity_links(conn, project_id)
    message = format_conflict_alert(node_name, claims)
    for claim in claims:
        slack_user_id = resolve_slack_recipient(claim, identity_links)
        if not slack_user_id:
            continue
        if has_action_been_taken(conn, project_id, node_id, "conflict_alert", slack_user_id):
            continue
        try:
            send_dm(slack_user_id, message)
        except Exception:
            logger.warning("conflict alert DM to %s failed for node %s", slack_user_id, node_id, exc_info=True)
            continue
        record_action(conn, project_id, node_id, "conflict_alert", slack_user_id, message)


def _classify_github_event_type(payload: dict) -> str:
    if "pull_request" in payload:
        return "pull_request"
    if "issue" in payload:
        return "issue"
    if "commits" in payload:
        return "push"
    return "unknown"


def _log_github_event(project_id: uuid.UUID, payload: dict) -> None:
    with get_conn() as conn:
        log_event(conn, project_id, "github", _classify_github_event_type(payload), payload, datetime.now(timezone.utc))


def _process_github_event(project_id: uuid.UUID, payload: dict) -> int:
    """Runs the extraction + DB writes off the event loop (blocking psycopg/openai calls)."""
    extraction = extract(json.dumps(payload))
    subject = payload.get("issue") or payload.get("pull_request") or {}
    source_ref = str(subject.get("number", ""))
    content = json.dumps(payload)[:2000]
    url = payload.get("repository", {}).get("html_url")
    author = subject.get("user", {}).get("login")

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
            author=author[:128] if author else None,
        )


def _slack_ts_to_datetime(ts: str | None) -> datetime:
    if not ts:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _log_slack_event(project_id: uuid.UUID, payload: dict) -> None:
    with get_conn() as conn:
        log_event(conn, project_id, "slack", payload.get("event", {}).get("type", "unknown"), payload, datetime.now(timezone.utc))


def _process_slack_event(project_id: uuid.UUID, event: dict) -> int:
    """Runs the extraction + DB writes off the event loop, same as GitHub events."""
    text = event["text"][:2000]
    extraction = extract(text)
    content = text
    occurred_at = _slack_ts_to_datetime(event.get("ts"))
    author = event.get("user")

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
            author=author[:128] if author else None,
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

    await run_in_threadpool(_log_github_event, project_id, payload)
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
    project_id = _default_project_id()

    if event.get("type") == "message":
        # Logged before the subtype/bot/text filter below, so the full human-message
        # history is retained even for messages extraction later decides to ignore.
        await run_in_threadpool(_log_slack_event, project_id, payload)

    if event.get("type") != "message" or event.get("subtype") or event.get("bot_id") or not event.get("text"):
        return {"status": "ignored"}

    entity_count = await run_in_threadpool(_process_slack_event, project_id, event)
    return {"status": "processed", "entities": entity_count}


@router.get("/projects/{project_id}/graph", dependencies=[Depends(require_api_key)])
def project_graph(project_id: uuid.UUID):
    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        return get_graph(conn, project_id)


def _compute_conflicts(conn, project_id: uuid.UUID) -> list[dict]:
    now = datetime.now(timezone.utc)
    conflicts = []
    for node in get_conflicted_nodes(conn, project_id):
        claims = get_state_changes_for_node(conn, node["id"])
        conflicts.append({"node": node, "claims": rank_claims(claims, now, RECENCY_HALF_LIFE_SECONDS)})
    return conflicts


@router.get("/projects/{project_id}/conflicts", dependencies=[Depends(require_api_key)])
def project_conflicts(project_id: uuid.UUID):
    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        conflicts = _compute_conflicts(conn, project_id)

    return {"conflicts": conflicts}


@router.get("/projects/{project_id}/risks", dependencies=[Depends(require_api_key)])
def project_risks(project_id: uuid.UUID):
    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        graph = get_graph(conn, project_id)

    return {"risks": detect_risks(graph["nodes"], graph["edges"])}


@router.get("/projects/{project_id}/deadlines", dependencies=[Depends(require_api_key)])
def project_deadlines(project_id: uuid.UUID):
    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        graph = get_graph(conn, project_id)

    today = datetime.now(timezone.utc).date()
    return {"crossed_deadlines": find_crossed_deadlines(graph["nodes"], graph["edges"], today)}


@router.get("/projects/{project_id}/dashboard", dependencies=[Depends(require_api_key)])
def project_dashboard(project_id: uuid.UUID):
    """One at-a-glance bundle (PRD.md §10.1) instead of the frontend firing four separate
    requests (graph/conflicts/risks/deadlines) on load."""
    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        graph = get_graph(conn, project_id)
        conflicts = _compute_conflicts(conn, project_id)

    today = datetime.now(timezone.utc).date()
    return {
        "counts": summarize_node_counts(graph["nodes"], graph["edges"]),
        "risks": detect_risks(graph["nodes"], graph["edges"]),
        "conflicts": conflicts,
        "crossed_deadlines": find_crossed_deadlines(graph["nodes"], graph["edges"], today),
    }


class InvestigateRequest(BaseModel):
    project_id: uuid.UUID
    question: str = Field(min_length=1, max_length=500)


_SEMANTIC_EVIDENCE_LIMIT = 25
_RECENT_EVIDENCE_LIMIT = 25


def _gather_evidence(conn, project_id: uuid.UUID, question: str) -> tuple[list[dict], bool]:
    """Blends evidence relevant to the question (semantic search) with evidence relevant
    to "what's happening right now" (recency) — a pure recency window misses old context;
    pure relevance misses fresh activity the question didn't ask about by name."""
    try:
        query_embedding = embed_text(question)
        semantic = search_evidence_by_similarity(conn, project_id, query_embedding, limit=_SEMANTIC_EVIDENCE_LIMIT)
    except Exception:
        semantic = []  # degrade to recency-only rather than failing the whole question

    recent = get_evidence_for_project(conn, project_id, limit=_RECENT_EVIDENCE_LIMIT)

    seen: set = set()
    combined = []
    for row in semantic + recent:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        combined.append(row)

    return combined, len(recent) >= _RECENT_EVIDENCE_LIMIT


@router.post("/agent/investigate", dependencies=[Depends(require_api_key), Depends(enforce_llm_rate_limit)])
def agent_investigate(payload: InvestigateRequest):
    with get_conn() as conn:
        if not project_exists(conn, payload.project_id):
            raise HTTPException(status_code=404, detail="unknown project")

        graph = get_graph(conn, payload.project_id)
        evidence, evidence_truncated = _gather_evidence(conn, payload.project_id, payload.question)
        context = {
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "conflicts": _compute_conflicts(conn, payload.project_id),
            "risks": detect_risks(graph["nodes"], graph["edges"]),
            "crossed_deadlines": find_crossed_deadlines(graph["nodes"], graph["edges"], datetime.now(timezone.utc).date()),
            "evidence": evidence,
            "evidence_truncated": evidence_truncated,
        }

    # Only the answer is returned — context (including raw evidence.content/url) is never
    # echoed back; it exists only to ground the LLM call, not as an API response payload.
    answer = answer_question(payload.question, context)
    return {"answer": answer}


def run_staleness_sweep(conn, project_id: uuid.UUID) -> list[uuid.UUID]:
    """Marks KNOWN nodes with no evidence within STALENESS_THRESHOLD_DAYS as UNKNOWN.
    Returns the node ids that were marked. Called both by the manual sweep route below
    and by the periodic background loop (see app/background.py)."""
    nodes = get_node_last_activity(conn, project_id)
    stale_ids = find_stale_nodes(nodes, datetime.now(timezone.utc), STALENESS_THRESHOLD_DAYS)
    mark_nodes_unknown(conn, stale_ids)
    return stale_ids


@router.post("/projects/{project_id}/sweep", dependencies=[Depends(require_api_key)])
def project_sweep(project_id: uuid.UUID):
    """Manually triggers the staleness sweep immediately, rather than waiting for the
    periodic interval — useful for demos and testing (see docs/roadmap-v2.md)."""
    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        stale_ids = run_staleness_sweep(conn, project_id)

    return {"marked_unknown": stale_ids}
