# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Project Brain is an evidence-backed project state engine: it ingests GitHub/Slack activity, extracts
entities/relationships/state via NVIDIA Nemotron (Nebius Token Factory), maintains a Postgres graph, and
detects conflicts and downstream risk. Product scope is in `PRD.md`; architecture decisions are in
`TechStack.md`. Read both before making product-shape changes — they're the source of truth this codebase
was built against, and several implementation choices (e.g. recency-only conflict scoring, no source-trust
weighting) were explicit product decisions recorded there, not oversights.

## Commands

### Backend (`backend/`)

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt   # first-time setup
.venv/bin/pytest                                                        # run all tests
.venv/bin/pytest tests/test_risk.py::test_detect_risks_only_flags_conflicted_nodes_with_downstream_impact  # single test
```

Use `python3.12`, not the bare `python3` — on macOS that's often an older Xcode-bundled Python (3.9), and
some modules rely on PEP 604 `X | None` syntax guarded by `from __future__ import annotations`. The
production Dockerfile targets `python:3.12-slim`.

All backend tests are self-contained (pure functions, or FastAPI's `TestClient` hitting only routes/paths
that short-circuit before touching a real database or the Nebius API) — no live Postgres or API key is
needed to run the suite.

### Frontend (`frontend/`)

```bash
npm install
npx tsc -b        # type-check (no build step needed to verify correctness)
npm run dev       # Vite dev server
```

### Full stack

```bash
cp .env.example .env   # fill in real values
docker compose up
psql "$DATABASE_URL" -f database/migrations/0001_init.sql -f database/migrations/0002_state_changes.sql
psql "$DATABASE_URL" -f database/seed/demo_project.sql
```

`docker-entrypoint-initdb.d` (mounted from `database/migrations/`) only runs on a *fresh* Postgres data
volume — reapplying to an existing running container needs the manual `psql` commands above.

## Architecture

### Single-project MVP, not multi-tenant

There is exactly one project, identified by `DEFAULT_PROJECT_ID` (env var). Webhook routes write into it
unconditionally; there's no repo→project or channel→project mapping. This is a deliberate scope decision
(PRD.md's non-goals exclude multi-project support from the MVP), not a missing feature — search for
`# ponytail:` comments for the documented upgrade path if that ever needs to change.

### Two separate auth boundaries — do not conflate them

- `POST /events/github` and `POST /events/slack` are authenticated by their **own webhook signature**
  (HMAC-SHA256 / Slack's `v0=` scheme) — never by `X-API-Key`. GitHub and Slack cannot attach custom
  headers to their own deliveries, so gating these behind an API key would 401 every real event and block
  Slack's mandatory `url_verification` handshake outright (this was a real bug caught and fixed mid-project;
  see the slice-1 commit).
- Every first-party route (`/projects/{id}/graph|conflicts|risks`, `/agent/investigate`) requires
  `X-API-Key`, checked in `app/security.py`. It's one shared secret, not per-user auth — there are no
  accounts anywhere in this system.
- `/agent/investigate` additionally goes through `enforce_llm_rate_limit` (also in `security.py`): it's the
  only route with real per-call LLM billing cost, so it gets its own naive in-process sliding-window limit
  on top of the shared API key.

### Extraction is the trust boundary, not the LLM's output schema

`app/agents/extraction.py`'s `extract()` calls Nemotron with `response_format={"type": "json_object"}`,
which only guarantees *syntactically valid JSON* — not valid values. `_filter_extraction()` is the actual
enforcement point: it allow-lists node types and relationship kinds, requires every `isinstance(x, str)`
check to happen *before* any `in <set>` membership test (a non-string value there previously caused an
uncaught `TypeError` crash — regression-tested in `test_extraction_filter.py`), and caps every list to
`MAX_EXTRACTION_ITEMS` so one crafted webhook payload can't grow the graph unbounded. Any code that adds a
new extracted field must filter it the same way before it reaches `graph/repository.py`.

### Conflict detection: recency only, never auto-resolved

`app/agents/reconciliation.py` scores each claim by `exp(-age / half_life)` — recency only, deliberately
*not* weighted by source trust (a product decision, not a gap). A node's `status` (`KNOWN`/`CONFLICTED`) is
recomputed from its *entire* claim history after every write, inside `_write_extraction_to_graph()` in
`app/api/routes.py`, under a `lock_node()` row lock — without that lock, two near-simultaneous GitHub+Slack
writes to the same entity can each miss the other's uncommitted claim and both write `KNOWN`, silently
swallowing the exact conflict this feature exists to catch (this was a real race found in review). A
conflict is never picked a winner and overwritten; it stays `CONFLICTED` until new evidence resolves it.

### Risk detection: BFS over BLOCKS/DEPENDS_ON from conflicted nodes

`app/agents/risk.py` does a cycle-safe BFS (via `collections.deque`, not `list.pop(0)`) from every
`CONFLICTED` node along `BLOCKS`/`DEPENDS_ON` edges to find downstream dependents. Both relationship types
are treated as propagating risk in the same `source → target` direction, even though "blocks" and "depends
on" have opposite real-world causality — a deliberate simplification matching PRD.md's own diagram
convention, documented inline rather than modeled precisely.

### Agent investigation is the one place output isn't schema-filtered

`app/agents/investigation.py`'s `answer_question()` is the only LLM call producing free text instead of a
validated JSON shape, because the point is a natural-language answer. It's grounded by assembling the
*entire* graph/conflicts/risks/evidence into a `context` dict and instructing the model (via a `system`
message, kept separate from the untrusted evidence text) to answer only from that data and never treat it
as instructions. The route intentionally returns only `{"answer": ...}` — it does not echo `context` back,
since that would leak raw evidence content/URLs through an API response with no frontend consumer for it.

### Frontend

Single-page tab switcher (`App.tsx`: Graph / Conflicts / Risks / Agent), no router — deliberately, since
four `useState`-driven tabs don't need one. `api/client.ts` centralizes every fetch call and attaches
`X-API-Key` from `VITE_API_KEY`; any new backend route needs a matching function there rather than an
inline `fetch()` in a component.
