# Project Brain — Roadmap v4: Branch-Aware Graph, RAG Visibility, Professional Redesign, Demo Data

**Status**: planned, not yet built. Produced via `/plan` (ecc:plan), conversational mode.

## Requirements restatement

Four requests bundled together, each grounded against what's already in the codebase:

1. **"Vector store for Slack embeddings so we can implement RAG"** — this is **already built**, not new work. Every evidence write (GitHub/Slack/Google Chat) already computes a Qwen3-Embedding-8B vector and stores it in `evidence.embedding` (pgvector, `backend/app/agents/embeddings.py`), and `POST /agent/investigate` already blends semantic similarity search with recency (`_gather_evidence` in `routes.py:629`) to ground its answers — that *is* RAG. What's actually missing: the route deliberately never returns which evidence it used (`routes.py:673`'s comment: "context... is never echoed back... since that would leak raw evidence content/URLs through an API response with no frontend consumer for it"). Now that we want a consumer (a citations UI), that decision needs to be revisited on purpose, not bypassed. **Scope for this plan: surface retrieved evidence as visible sources in the Agent chat UI** — not rebuilding a vector store that already exists.
2. **Branch-based graph page** — the graph today (`GraphView.tsx`) is a flat ReactFlow grid of every extracted entity with no grouping. The ask: organize it around git branches — what each branch is solving, the main branch, deadlines/milestones at risk — the things a PM actually scans for. GitHub's `pull_request` webhook payload already carries `head.ref` (branch) and `base.ref` (target, usually `main`) on every PR event we already ingest — no new GitHub event subscription needed, just new deterministic (non-LLM) parsing of a field we already receive, plus two new node types (`BRANCH`, `MILESTONE`) and a redesigned graph page that groups by branch instead of a flat grid.
3. **Professional dashboard/graph styling** — current `Dashboard.tsx`/`GraphView.tsx` are functional but plain (default Tailwind utility boxes, no type scale, no real visual hierarchy). Needs a real design pass, not a new UI library (Tailwind's already there and is enough per the project's existing lazy-dependency convention).
4. **Demo data — realistic messages actually visible in a real Slack channel** — `backend/scripts/demo_events.py` already replays signed synthetic events straight to our webhook routes (bypassing Slack entirely), which is fast but invisible in Slack itself. Since the ask is specifically "in the Slack group" for a watchable demo, this needs a variant that posts through Slack's real `chat.postMessage` API (using `SLACK_BOT_TOKEN`, already configured and proven working this session) into the actually-connected demo channel, so messages appear for real and flow back through the real event pipeline — same authenticity as the "HELLO GUYS" test, but a written, coherent story instead of one line. The user explicitly called this "later on," so it's sequenced last.

## Patterns to mirror

| Category | Source | Pattern |
|---|---|---|
| Node/relationship allow-list | `backend/app/agents/extraction.py:11-12` | `ALLOWED_NODE_TYPES`/`ALLOWED_RELATIONSHIPS` sets, checked in `_filter_extraction` — the real trust boundary, not the LLM's output schema |
| Deterministic (non-LLM) graph writes | `backend/app/api/routes.py` GitHub App install flow | Not everything goes through `extract()` — installation/connection data is written directly from payload fields GitHub already gives us structurally |
| Repository functions | `backend/app/graph/repository.py` | Thin functions taking `conn` first, `upsert_node`/`upsert_edge` already exist and are type-agnostic (no schema change needed for new node types — `nodes.type` is free-text, confirmed via `\d nodes`, no CHECK constraint) |
| RAG retrieval | `backend/app/api/routes.py:629` `_gather_evidence` | Blends `search_evidence_by_similarity` (semantic) with `get_evidence_for_project` (recency), degrades to recency-only on embedding failure |
| Outbound Slack | `backend/app/outbound/slack.py` `send_dm` | httpx + Bearer `SLACK_BOT_TOKEN`, raises on failure, caller decides how to degrade |
| Demo/replay scripts | `backend/scripts/demo_events.py` | Signed synthetic payloads posted straight to webhook routes; loads `.env` via `dotenv`, prints each response |
| Frontend data fetching | `frontend/src/api/client.ts` | One typed fetch function per route, `X-API-Key` via `authHeaders()` |
| Tests | `backend/tests/test_*.py` | `TestClient`, `os.environ.setdefault` for required config before import, monkeypatch for anything that would hit a real network/DB call |

## Files to change

| File | Action | Why |
|---|---|---|
| `backend/app/agents/extraction.py` | UPDATE | Add `MILESTONE` to `ALLOWED_NODE_TYPES` and a relationship for it (e.g. `PART_OF`) so Nemotron can tag milestone mentions in Slack/GitHub text |
| `backend/app/api/routes.py` | UPDATE | Deterministic branch/PR-state parsing in `_process_github_event`; new `_gather_evidence` sources surfaced in `/agent/investigate`'s response; new `GET /projects/{id}/branches` read route |
| `backend/app/graph/repository.py` | UPDATE (maybe) | Only if a branch-specific query (e.g. "nodes grouped by branch") can't be expressed by the existing generic `get_graph` + client-side grouping — decide during Task 1 |
| `frontend/src/graph/GraphView.tsx` | REWRITE | Branch-swimlane layout instead of flat grid; visual distinction for `main`/default branch |
| `frontend/src/dashboard/Dashboard.tsx` | UPDATE | Restyle with a real design system; add milestone/branch-at-risk summary if Task 1 produces that data |
| `frontend/src/agent/AgentChat.tsx` | UPDATE | Render returned sources under each answer |
| `frontend/src/index.css` (or wherever Tailwind config lives) | UPDATE | Design tokens: color palette, type scale, shared card/badge primitives |
| `backend/scripts/demo_scenario_slack.py` | CREATE | Posts a realistic multi-message story to a real connected Slack channel via `chat.postMessage` |
| `backend/tests/test_branch_extraction.py` | CREATE | Deterministic branch parsing from PR payloads |
| `docs/roadmap-v4-branches-rag-polish.md` | UPDATE | Mark tasks done as they land, same convention as v2/v3 |

## Tasks

### Phase 1 — Branch-aware graph model [DONE]
- **Task 1.1** [DONE]: Added deterministic branch parsing (`_upsert_pr_branches` in `routes.py`): on any `pull_request` event, upserts a `BRANCH` node for `head.ref` and `base.ref`, tagging whichever matches `repository.default_branch` with `metadata: {"is_default": true}`. Upserts an edge `PR node -[ON_BRANCH]-> BRANCH node`, but only when a `PULL_REQUEST` node with that exact title already exists (via new `find_node_id_by_name`) — deliberately never creates/overwrites the PR node itself here, to avoid racing `_write_extraction_to_graph`'s claim-reconciliation status logic. Live-verified: a synthetic signed PR event produced `BRANCH` nodes for `main` (`is_default: true`) and the feature branch, plus the `ON_BRANCH` edge.
- **Task 1.2** [DONE]: Added `MILESTONE`/`PART_OF` to the extraction allow-list and prompt. Live-verified in the same test event — Nemotron correctly extracted a `MILESTONE` ("beta launch") and a `PART_OF` edge from the PR body text.
- **Task 1.3** [SKIPPED — not needed]: `get_graph` already returns every node's `type`/`status`/`metadata` and every edge's `relationship`, which is everything the frontend needs to derive branch grouping (filter `type == "BRANCH"`, follow `ON_BRANCH` edges) without a dedicated endpoint duplicating that data. Revisit only if Phase 3's frontend work finds a real need for server-side grouping.

### Phase 2 — RAG visibility [DONE]
- **Task 2.1** [DONE]: `POST /agent/investigate` returns `sources` — deduped by `(node_name, source_type)` and capped to `_MAX_RETURNED_SOURCES` (6), since the raw blended evidence list can carry the same node dozens of times (e.g. a repo entity attached to every GitHub event). Never includes raw `content`.
- **Task 2.2** [DONE]: `AgentChat.tsx` renders a "Based on:" line per answer, linking out when a source has a `url`. Live-verified in-browser: a real question returned a correct answer plus exactly 6 distinct, deduped sources.

### Phase 3 — Professional redesign [DONE]
- **Task 3.1** [DONE]: Design tokens added to `tailwind.config.js` (Inter/JetBrains Mono via Google Fonts, `ink`/`muted`/`surface`/`panel`/`border`/`accent`/`status.*` color tokens, `shadow-card`/`rounded-card`) plus shared `.card`/`.badge-*`/`.btn-primary`/`.btn-secondary` component classes in `index.css`. New `frontend/src/lib/nodeStatus.ts` mirrors the backend's exact `active`/`blocked`/`conflicted`/`unknown` classification so colors stay consistent everywhere.
- **Task 3.2** [DONE]: `GraphView.tsx` rewritten as branch swimlanes — one column per `BRANCH` node (main first, visually distinct with an accent border), a PR's connected nodes pulled into its branch's column via `ON_BRANCH` + one more hop of direct neighbors, everything else bucketed into an "Unassigned" column. Live-verified: the demo project correctly rendered `main`, the `refactor-ocr-pipeline` branch (with its PR, author, and linked milestone), and older pre-branch-tracking demo entities under Unassigned.
- **Task 3.3** [DONE]: `Dashboard.tsx` restyled on the new tokens (colored left-border stat cards, `.card` sections, badge chips). "Branches at risk" summary skipped — `DashboardResponse` doesn't carry per-branch data and Task 1.3 (a dedicated branches endpoint) was deliberately skipped as unnecessary; revisit only if a real need shows up.
- **Extra (not originally listed, done for visual cohesion)**: `App.tsx`'s header/nav, `ConflictView.tsx`, `RiskPanel.tsx`, and `AgentChat.tsx`'s remaining hardcoded colors also moved onto the same tokens, so the whole app reads as one consistent design instead of two polished tabs next to three unstyled ones.

### Phase 4 — Demo data (sequenced last, per "later on")
- **Task 4.1**: `backend/app/outbound/slack.py` gets a `post_message(channel_id, text)` function (mirrors `send_dm`, posts to a channel instead of opening a DM).
- **Task 4.2**: `backend/scripts/demo_scenario_slack.py` — a scripted, realistic multi-message conversation (a sprint with 2-3 branches, a blocking dependency, a missed deadline, a conflicting status update) posted with small delays into the real connected demo channel via `post_message`, so it's watchable live in Slack and flows back through the real webhook pipeline exactly like the "HELLO GUYS" test.
  - **Validate**: run against the real connected workspace, confirm messages appear in Slack and extract into the graph.

## Validation
```bash
cd backend && .venv/bin/pytest
cd frontend && npx tsc -b
docker compose up -d --build backend frontend
```

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Reversing the "never echo evidence" decision leaks more than intended if the sources payload isn't kept minimal | Medium | Explicit allow-list of fields in the `sources` shape (Task 2.1), never raw `content` |
| Branch swimlane layout gets unwieldy on a repo with many long-lived branches | Medium | Scope to open/recently-active branches by default; exact cutoff TBD during Task 3.2 |
| "Professional" styling is subjective without a reference | Medium | Task 3.1 proposes concrete tokens before any component rewrite — flag for a quick visual check-in rather than guessing to completion |
| Demo script posting real messages could pollute the demo project's real graph data | Low | Already-accepted tradeoff — same as the "HELLO GUYS" test; can always start a fresh project for a demo |

## Acceptance
- [ ] Phase 1: PR events produce `BRANCH` nodes and `ON_BRANCH` edges; `MILESTONE` extractable; `GET /projects/{id}/branches` live
- [ ] Phase 2: `/agent/investigate` returns safe `sources`; AgentChat UI shows them
- [ ] Phase 3: Graph page shows branch swimlanes on the new design tokens; Dashboard restyled
- [ ] Phase 4: Demo script posts a realistic story into a real Slack channel and it ingests correctly
- [ ] All existing tests still pass; new tests added per task

## Open assumptions (correct via "modify:" if wrong)
- "Branches" means literal git branches (via PR payload `head.ref`/`base.ref`), not a conceptual grouping like epics/initiatives.
- RAG scope is "make existing retrieval visible," not a second vector store or different retrieval mechanism.
- No new frontend UI library — redesign stays in Tailwind.
- Dark mode is out of scope unless you say otherwise.

**WAITING FOR CONFIRMATION**: proceed with this plan, or reply `modify: ...` with changes?
