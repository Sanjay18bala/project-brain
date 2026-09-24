# Project Brain — Roadmap v3: Multi-Tenant Self-Service Onboarding

**Status**: DONE. All 6 tasks built, tested, and live-verified end to end — a PM can create a project in the
UI, click Connect GitHub, install the real GitHub App, and have inbound webhook events route to their
project via the `connections` table, with no engineer involved after initial deployment.

**Decision history**: this plan originally used a GitHub App with OAuth-during-installation. It was then
briefly simplified to a per-project webhook secret (no OAuth, PM pastes a URL+secret into GitHub's plain
webhook form themselves) to cut build complexity. Reverted back to the GitHub App design: the simpler
version is genuinely less work to build, but it's a worse experience for the PM — a multi-step copy-paste
with a raw secret to mishandle, versus one click on GitHub's own install screen where they pick exactly
which repos to share and can revoke access from a place they already know. Since the actual goal is a real
product people trust enough to connect their real GitHub org to, the GitHub App is the right call even
though it's more work.

## Requirements restatement

Today there is exactly one project (`DEFAULT_PROJECT_ID`, a single env var), and every platform
connection (GitHub webhook, Slack app, Google Chat app) requires an engineer to manually configure it in
that platform's own console and copy secrets into `.env` by hand. The goal: a PM can create their own
project and connect their own GitHub org through the product itself, with no engineer involved after
initial deployment. This plan covers **GitHub only**, end to end, to prove the pattern before Slack and
Google Chat get their own (separate, later) plans.

## Pattern grounding (existing conventions this should mirror)

| Category | Source | Pattern |
|---|---|---|
| Ingestion module | `backend/app/ingestion/{github,slack,googlechat}.py` | One small module per platform, a single `verify_*` function, no DB access |
| Repository access | `backend/app/graph/repository.py` | Every DB call takes `conn` as first arg, parameterized queries, `dict(zip(cols, row))` result shaping |
| Route auth | `backend/app/api/routes.py` | Webhook routes authenticate via the platform's own signature, never `X-API-Key`; first-party routes use `Depends(require_api_key)` |
| Graceful degradation | `_send_conflict_alerts` in `routes.py` | External-call failures are caught, logged via `logger.warning(..., exc_info=True)`, never break the request |
| Migrations | `database/migrations/000N_*.sql` | One numbered file per slice, applied via `docker-entrypoint-initdb.d` on fresh volumes, manual `psql` on a live one |
| Tests | `backend/tests/test_*.py` | Pure logic gets direct unit tests; anything needing a real external signature (like this OAuth flow) gets monkeypatched tests, same as `test_googlechat_ingestion.py` |

No existing pattern for: project CRUD (only ever seeded via raw SQL), OAuth token exchange, or per-project
(vs. global) webhook routing. These are genuinely new territory, not just repetition of an existing shape.

## Files to change

| File | Action | Why |
|---|---|---|
| `database/migrations/0007_projects_and_connections.sql` | CREATE | Adds real project creation (`projects` already exists as a table but nothing ever inserts into it except the seed script) and the `connections` table |
| `backend/app/graph/repository.py` | UPDATE | Add `create_project`, `list_projects`, `create_connection`, `get_project_id_for_installation` |
| `backend/app/config.py` | UPDATE | Add `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_APP_SLUG`, `GITHUB_APP_CALLBACK_URL` |
| `backend/app/integrations/github_app.py` | CREATE | OAuth token exchange + "list installations for this user" API calls |
| `backend/app/api/routes.py` | UPDATE | New `POST /projects`, `GET /projects`, `GET /connections/github/install`, `GET /connections/github/callback` routes; `_process_github_event` resolves `project_id` from the installation, not `_default_project_id()` |
| `backend/tests/test_github_app_connection.py` | CREATE | Monkeypatched tests for the callback's installation-ownership check (can't fabricate a real GitHub OAuth code, same limitation as `test_googlechat_ingestion.py`) |
| `frontend/src/projects/` | CREATE | Project switcher + "Create Project" + "Connect GitHub" button |
| `README.md` | UPDATE | GitHub App creation steps (replacing the current manual-webhook instructions) |

## Tasks

### Task 1: `projects` and `connections` tables
- **Action**: migration adding real project creation (name, created_at already exist on `projects`;
  nothing changes there) and:
  ```sql
  CREATE TABLE connections (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      platform TEXT NOT NULL,
      external_id TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (platform, external_id)
  );
  ```
  `external_id` for GitHub is the installation id (a string). `UNIQUE (platform, external_id)` means one
  GitHub installation maps to exactly one project — installing on the same org twice for two different
  projects is rejected, not silently overwritten.
- **Mirror**: `database/migrations/0006_slice10_alerting.sql`'s shape (comment explaining *why*, plain
  `CREATE TABLE`, a `UNIQUE` constraint backing a business rule at the DB level).
- **Validate**: `psql "$DATABASE_URL" -f database/migrations/0007_projects_and_connections.sql` against a
  fresh and an existing container, both clean.

### Task 2: Project CRUD API + repository functions
- **Action**: `create_project(conn, name) -> uuid`, `list_projects(conn) -> list[dict]` in
  `repository.py`; `POST /projects` (`{"name": str}`, guarded by `X-API-Key`, same as every other
  first-party route), `GET /projects` (list, for the frontend switcher).
- **Mirror**: `project_exists`/existing route shape in `routes.py` — thin route, real logic in
  `repository.py`.
- **Validate**: `pytest` (repository functions aren't unit-tested directly per existing convention — no
  DB in CI — verified live via `curl` against the running container, same as every other slice this
  session).

### Task 3: GitHub App registration (external, only you can do this)
- **Action**: you create a GitHub App (not a plain OAuth App) at github.com/settings/apps/new:
  - Webhook URL: your public `/events/github` (same as today)
  - Webhook secret: same `GITHUB_WEBHOOK_SECRET` value already in `.env` — **no change to
    `verify_github_signature` at all**, since a GitHub App still has one webhook secret per app, checked
    identically to today's shared-secret model
  - Permissions: Issues (Read), Pull requests (Read) — read-only, matches our ingestion-only use case
  - Subscribe to events: Issues, Pull request
  - **Request user authorization (OAuth) during installation**: checked — this is what makes the
    callback include a `code` we can exchange for a token, closing the spoofed-`installation_id` gap
  - Where can this be installed: Any account
- I'll tell you exactly what to fill in, mirroring how we did the Nebius API key.

### Task 4: Connect flow — install redirect + callback [DONE — commit `dfcc5af`]
- **Action**:
  - `GET /connections/github/install?project_id=<uuid>` → redirect to
    `https://github.com/apps/<GITHUB_APP_SLUG>/installations/new?state=<project_id>` (confirmed via
    GitHub's own docs: `state` **is** preserved through this specific URL, unlike the plain setup URL).
  - `GET /connections/github/callback?installation_id=...&code=...&state=...`:
    1. Exchange `code` for a user access token (`POST github.com/login/oauth/access_token` with
       `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET`).
    2. Call `GET api.github.com/user/installations` with that token; confirm `installation_id` from the
       query string is actually in the returned list.
    3. Only if confirmed: `create_connection(conn, project_id=state, platform="github",
       external_id=installation_id)`.
    4. If not confirmed: reject with a 403 — this is the exact check that closes the spoofing gap GitHub's
       docs warn about.
- **Mirror**: `_send_conflict_alerts`'s try/except-and-log shape for the outbound GitHub API calls in step
  1/2 — a failure here should return a clear error to the PM's browser, not a silent 500.
- **Validate**: can't fabricate a real GitHub OAuth `code` any more than we could a Slack/Google signature
  — monkeypatched tests cover our own logic (installation-not-in-list → 403, token exchange failure →
  clear error), same limitation documented for `test_googlechat_ingestion.py`. Live verification needs an
  actual GitHub App and a real install click, done together once Task 3 is complete.

### Task 5: Route incoming GitHub events by installation, not `DEFAULT_PROJECT_ID` [DONE — commit `dfcc5af`]
- **Action**: in `receive_github_event`, after the (unchanged) HMAC verification, resolve `project_id` via
  the new `_resolve_github_project_id` helper: reads `payload["installation"]["id"]`, calls
  `get_project_id_for_installation`. If no connection is found, returns 200 with `{"status": "ignored"}`
  (an uninstalled/unknown installation should not error loudly to GitHub, which would trigger webhook
  retries) rather than 404. **`DEFAULT_PROJECT_ID`'s fate, decided**: kept as an explicit fallback — a
  payload with no `installation` field at all (pre-App/legacy webhook shape) still routes to the demo
  project rather than being dropped, so existing demo data stays intact.
- **Mirror**: the existing `_default_project_id()` docstring already names this exact upgrade path (written
  back in Slice 1): *"map GitHub repo full_name / Slack team_id+channel to a project via a lookup table
  once multi-project support lands."* This task is that upgrade, for GitHub.
- **Validate**: once Task 3/4 are live, re-run something like `demo_events.py` but signed with the real
  app's webhook secret and carrying a real `installation.id`, confirming it lands in the right project.

### Task 6: Frontend — project switcher + Connect button [DONE]
- **Action**: replace the hardcoded `VITE_DEMO_PROJECT_ID` with a project list fetched from `GET
  /projects`, a switcher in the header, a "New Project" form, and a "Connect GitHub" button that hits
  `GET /connections/github/install?project_id=...`.
- **Mirror**: `frontend/src/api/client.ts`'s existing fetch-function pattern; `App.tsx`'s tab-switcher
  `useState` pattern, extended to also track the selected project.
- **Validate**: `npx tsc -b`, then a manual click-through once the backend pieces are live.

## Validation

```bash
cd backend && .venv/bin/pytest
cd frontend && npx tsc -b
# Live, once a real GitHub App exists:
#   create a project via POST /projects, click Connect GitHub, install on a real repo,
#   open an issue, confirm it lands in that project's graph (not the old demo project's).
```

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Spoofed `installation_id` linking someone else's GitHub org to your project | Was high before this plan; closed by Task 4's user-token ownership check | Confirmed via GitHub's own docs before designing this, not discovered after shipping |
| GitHub API rate limits on the token-exchange/installations-list calls during a connect | Low at this scale | Not mitigated now; would need a retry/backoff if this becomes real traffic |
| `installation.id` may not be present on every GitHub event type (some legacy/marketplace events differ) | Low, since we only subscribe to Issues/Pull request | `get_project_id_for_installation` returning nothing degrades to "ignored," not a crash |
| This migration doesn't remove `DEFAULT_PROJECT_ID` — old data under the demo project needs a decision (migrate it to a real project row, or leave it as-is) | Certain, needs a decision before Task 5 ships | Flagging now rather than deciding unilaterally — ask before Task 5 |

## Explicitly out of scope for this plan

- Slack OAuth install flow (own plan, once GitHub proves the pattern)
- Google Chat multi-space routing (own plan)
- Encrypting the (currently none — this design stores no long-lived GitHub token, only a one-time
  exchange during connect) — worth re-checking if a future task needs to store a persistent token
- Disconnecting/removing a connection (DELETE flow) — not designed yet

## Estimated complexity: **Large**

This is the biggest single plan in the project's history — real OAuth, a new trust boundary, and the
removal of an assumption (`DEFAULT_PROJECT_ID`) baked into every webhook route. Rough sizing: Tasks 1-2
(Small, mechanical), Task 3 (external, your time not build time), Task 4 (Medium — the actual OAuth/
security-sensitive core), Task 5 (Small), Task 6 (Medium).

## Acceptance

- [ ] All tasks complete
- [ ] `pytest` and `tsc -b` both pass
- [ ] A real GitHub App installed on a real repo routes events to the correct project, verified live
- [ ] The spoofed-`installation_id` check is actually exercised by a test, not just designed
- [ ] `DEFAULT_PROJECT_ID`'s fate (kept as a fallback vs. removed) is a decision, not an oversight

**CONFIRMED**: proceeding with this plan (GitHub App + OAuth-during-installation).
