# Project Brain — Roadmap v3: Multi-Tenant Self-Service Onboarding

**Status**: planned, not yet built. Produced via `/plan` (ecc:plan), conversational mode. Revised once —
see "Why this is simpler than the first version" below.

## Requirements restatement

Today there is exactly one project (`DEFAULT_PROJECT_ID`, a single env var), and every platform
connection (GitHub webhook, Slack app, Google Chat app) requires an engineer to manually configure it in
that platform's own console and copy secrets into `.env` by hand. The goal: a PM can create their own
project and connect their own GitHub org through the product itself, with no engineer involved after
initial deployment. This plan covers **GitHub only**, end to end, to prove the pattern before Slack and
Google Chat get their own (separate, later) plans.

## Why this is simpler than the first version

The original version of this plan used a GitHub App with OAuth-during-installation, so we could verify
that whoever claimed an `installation_id` actually owned it (GitHub's own docs warn that `installation_id`
alone is spoofable). That's real, correct, and also genuinely the most complex thing in the project so
far — a new OAuth client, a token exchange, an ownership-verification call, a new kind of security bug to
get right.

Revised approach: skip GitHub Apps and OAuth entirely. Each project gets its **own generated secret** and
its **own webhook URL** (the project id is literally in the URL path). The PM pastes those two values into
a plain webhook on their own repo, the same way our current single demo project's webhook already works —
just parameterized per project instead of one global secret. This reuses `verify_github_signature`
unchanged, needs no client ID/secret, no callback, no ownership-verification step, and no new class of
security bug: the secret itself *is* the proof of ownership, exactly like every webhook we've already
shipped. The cost: the PM does one small copy-paste into GitHub's webhook form instead of one OAuth click.
That's the right trade for cutting out the riskiest, newest part of the system.

## Pattern grounding (existing conventions this should mirror)

| Category | Source | Pattern |
|---|---|---|
| Ingestion module | `backend/app/ingestion/{github,slack,googlechat}.py` | One small module per platform, a single `verify_*` function, no DB access |
| Repository access | `backend/app/graph/repository.py` | Every DB call takes `conn` as first arg, parameterized queries, `dict(zip(cols, row))` result shaping |
| Route auth | `backend/app/api/routes.py` | Webhook routes authenticate via the platform's own signature, never `X-API-Key`; first-party routes use `Depends(require_api_key)` |
| Migrations | `database/migrations/000N_*.sql` | One numbered file per slice, applied via `docker-entrypoint-initdb.d` on fresh volumes, manual `psql` on a live one |
| Tests | `backend/tests/test_*.py` | Pure logic gets direct unit tests; DB-touching code verified live via `curl`, same as every slice this session |

No existing pattern for: project CRUD (only ever seeded via raw SQL) or per-project (vs. global) webhook
secrets/routing. Both are new territory, but neither is a new *kind* of mechanism — they extend the
existing signature-verification pattern to be parameterized instead of global.

## Files to change

| File | Action | Why |
|---|---|---|
| `database/migrations/0007_projects_and_connections.sql` | CREATE | Real project creation, and a `connections` table: `project_id, platform, secret` |
| `backend/app/graph/repository.py` | UPDATE | Add `create_project`, `list_projects`, `create_connection`, `get_connection_secret` |
| `backend/app/api/routes.py` | UPDATE | New `POST /projects`, `GET /projects`, `POST /projects/{id}/connections/github`; `POST /events/github/{project_id}` replaces the global `/events/github` |
| `backend/app/ingestion/github.py` | UPDATE (maybe none) | `verify_github_signature` already takes `secret` as a parameter — likely unchanged, just called with a per-project secret instead of the global env var |
| `backend/tests/test_project_connections.py` | CREATE | Repository/route-level tests for connection creation and per-project signature verification |
| `frontend/src/projects/` | CREATE | Project switcher + "Create Project" + "Connect GitHub" screen showing the webhook URL/secret to copy |
| `README.md` | UPDATE | Replace the current manual single-webhook instructions with "create a project, copy the URL+secret it gives you, paste into GitHub" |

## Tasks

### Task 1: `projects` and `connections` tables
- **Action**:
  ```sql
  CREATE TABLE connections (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      platform TEXT NOT NULL,
      secret TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (project_id, platform)
  );
  ```
  One secret per project per platform — `UNIQUE (project_id, platform)` means re-connecting GitHub on the
  same project replaces its secret rather than creating a second row.
- **Mirror**: `database/migrations/0006_slice10_alerting.sql`'s shape (comment explaining *why*, plain
  `CREATE TABLE`, a `UNIQUE` constraint backing a business rule at the DB level).
- **Validate**: `psql "$DATABASE_URL" -f database/migrations/0007_projects_and_connections.sql` against a
  fresh and an existing container, both clean.

### Task 2: Project CRUD API + repository functions
- **Action**: `create_project(conn, name) -> uuid`, `list_projects(conn) -> list[dict]` in
  `repository.py`; `POST /projects` (`{"name": str}`, guarded by `X-API-Key`), `GET /projects` (list, for
  the frontend switcher).
- **Mirror**: `project_exists`/existing route shape in `routes.py` — thin route, real logic in
  `repository.py`.
- **Validate**: verified live via `curl` against the running container, same as every prior slice.

### Task 3: Generate a connection (secret + URL)
- **Action**: `create_connection(conn, project_id, platform, secret) -> None`, `get_connection_secret(conn,
  project_id, platform) -> str | None`. Route `POST /projects/{id}/connections/github` (guarded by
  `X-API-Key`) generates a random secret (`secrets.token_hex(32)`, stdlib — no new dependency), stores it,
  and returns `{"webhook_url": ".../events/github/{id}", "secret": "..."}` for the frontend to display.
- **Mirror**: `security.py`'s existing secret-comparison style (`hmac.compare_digest`) for how the secret
  gets *checked* later in Task 4; generation itself is new but uses only `secrets` from the stdlib.
- **Validate**: `curl -X POST .../projects/{id}/connections/github` returns a URL+secret; confirm the row
  landed in `connections` via `psql`.

### Task 4: Per-project webhook route
- **Action**: `POST /events/github/{project_id}` replaces the current global `POST /events/github`.
  Looks up that project's secret via `get_connection_secret`, calls the *unchanged*
  `verify_github_signature(body, signature, secret)` with it instead of the global
  `GITHUB_WEBHOOK_SECRET`. If no connection exists for that project_id, 404 (not "ignored" — unlike the
  installation-based design, an unrecognized project_id here means the URL itself is wrong, not a
  legitimate-but-uninstalled event).
- **Mirror**: today's `receive_github_event` almost exactly — same signature check, same
  `_log_github_event`/`_process_github_event` calls, just parameterized by `project_id` from the URL
  instead of `_default_project_id()`.
- **Validate**: sign a test payload with a real generated secret from Task 3, POST it to the per-project
  URL, confirm it lands in that project's graph — same pattern as every `demo_events.py`-style check this
  session.

### Task 5: Frontend — project switcher + Connect screen
- **Action**: replace the hardcoded `VITE_DEMO_PROJECT_ID` with a project list from `GET /projects`, a
  switcher in the header, a "New Project" form, and a "Connect GitHub" screen that calls Task 3's endpoint
  and displays the URL + secret with copy buttons and the exact GitHub steps (Settings → Webhooks → Add
  webhook → paste → select Issues/Pull request → Save).
- **Mirror**: `frontend/src/api/client.ts`'s fetch-function pattern; `App.tsx`'s tab-switcher `useState`
  pattern, extended to also track the selected project.
- **Validate**: `npx tsc -b`, then a manual click-through once the backend pieces are live.

## Validation

```bash
cd backend && .venv/bin/pytest
cd frontend && npx tsc -b
# Live: create a project, hit the connections endpoint, sign a test payload with the
# returned secret, POST it to the per-project URL, confirm it lands in the right project's graph.
```

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Someone guesses another project's webhook URL and tries garbage signatures against it | Low impact even if tried | Same HMAC verification already proven against real attacks this session — a guessed URL without the matching secret still fails signature check |
| PM pastes the secret somewhere insecure (their own mistake, not ours) | Real but outside our control | Regenerating a connection's secret (replacing the old one) is a cheap follow-up if this becomes a concern |
| This doesn't remove `DEFAULT_PROJECT_ID` — old demo-project data needs a decision (migrate to a real project row, or leave it as-is) | Certain, needs a decision before Task 4 ships | Flagging now rather than deciding unilaterally — ask before Task 4 |

## Explicitly out of scope for this plan

- Slack manual-connection flow (own plan, once GitHub proves the pattern — likely the same per-project-URL
  shape)
- Google Chat multi-space routing (own plan)
- Regenerating/rotating a connection's secret via the UI — not designed yet
- Disconnecting/removing a connection (DELETE flow) — not designed yet

## Estimated complexity: **Medium**

Downgraded from the original **Large** — no OAuth, no external app registration, no new security
mechanism, just parameterizing an existing, already-proven pattern. Rough sizing: Tasks 1-3 (Small,
mechanical, no external dependency), Task 4 (Small — mirrors an existing route), Task 5 (Medium, the real
frontend work).

## Acceptance

- [ ] All tasks complete
- [ ] `pytest` and `tsc -b` both pass
- [ ] A project created through the UI gets its own webhook URL + secret, and a real signed event routes
      to that specific project, verified live
- [ ] `DEFAULT_PROJECT_ID`'s fate (kept as a fallback vs. removed) is a decision, not an oversight

**WAITING FOR CONFIRMATION**: proceed with this plan? (yes / modify / different approach)
