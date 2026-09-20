from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from ..agents.extraction import extract
from ..config import GITHUB_WEBHOOK_SECRET
from ..db import get_conn
from ..graph.repository import add_evidence, get_graph, project_exists, upsert_edge, upsert_node
from ..ingestion.github import verify_github_signature
from ..security import require_api_key

router = APIRouter()


def _parse_project_id(raw: str | None) -> uuid.UUID:
    if not raw:
        raise HTTPException(status_code=400, detail="missing X-Project-Id header")
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="malformed project id") from None


def _process_event(project_id: uuid.UUID, payload: dict) -> int:
    """Runs the extraction + DB writes off the event loop (blocking psycopg/openai calls)."""
    extraction = extract(json.dumps(payload))

    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")

        node_ids: dict[str, uuid.UUID] = {}
        for entity in extraction["entities"]:
            node_ids[entity["name"]] = upsert_node(conn, project_id, entity["type"], entity["name"])

        for rel in extraction["relationships"]:
            upsert_edge(conn, project_id, node_ids[rel["source"]], node_ids[rel["target"]], rel["relation"])

        subject = payload.get("issue") or payload.get("pull_request") or {}
        source_ref = str(subject.get("number", ""))
        content = json.dumps(payload)[:2000]
        url = payload.get("repository", {}).get("html_url")
        for node_id in node_ids.values():
            add_evidence(conn, project_id, node_id, "github", source_ref, content, url, datetime.now(timezone.utc))

    return len(extraction["entities"])


@router.post("/events/github", dependencies=[Depends(require_api_key)])
async def receive_github_event(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(body, signature, GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="invalid signature")

    project_id = _parse_project_id(request.headers.get("X-Project-Id"))
    payload = json.loads(body)

    entity_count = await run_in_threadpool(_process_event, project_id, payload)
    return {"status": "processed", "entities": entity_count}


@router.get("/projects/{project_id}/graph", dependencies=[Depends(require_api_key)])
def project_graph(project_id: uuid.UUID):
    with get_conn() as conn:
        if not project_exists(conn, project_id):
            raise HTTPException(status_code=404, detail="unknown project")
        return get_graph(conn, project_id)
