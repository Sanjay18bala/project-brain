# Project Brain — Roadmap v2: Dynamic & Proactive

## Why this document exists

Slices 0–4 (see git log, `main` branch) built the reactive core: GitHub/Slack ingestion, conflict
detection, dependency/risk detection, and a pull-based agent chat. Testing it end-to-end (see
`backend/scripts/demo_events.py`) proved the pipeline works, but surfaced that it doesn't yet deliver on
the product's actual promise to a PM/team-lead: keep track of what's happening and *tell them*, not just
answer when asked. This doc captures the gap analysis, the expanded use-case list, and a slice plan for
closing it — written down so it survives a session ending abruptly.

## Root causes (why it feels thin today)

1. **Evidence is lossy.** A Slack/GitHub event only gets stored if extraction recognizes at least one
   entity in it. Everything else is discarded — there's no full raw history, despite the `events` table
   existing in the schema since `0001_init.sql`. Nothing has ever written a row into it.
2. **No semantic search.** `TechStack.md §7` planned pgvector-based retrieval over all evidence
   specifically so old context isn't lost. The `embedding` column exists on `evidence`; nothing has ever
   populated or queried it. The agent's only retrieval today is "the 50 most recent evidence rows,
   project-wide" — not scoped to what's actually relevant to the question.
3. **No sender identity.** Slack ingestion reads `event["text"]` and `event["ts"]`, never `event["user"]`.
   There is currently no way to answer "who sent this" at all.
4. **No staleness/Unknown detection.** `PRD.md §7.5` was P0 in the original scope — "no recent GitHub
   activity, most recent Slack reference is 3 days old, owner appears to have switched tasks" — and was
   never built in any of the four shipped slices. `UNKNOWN` exists only as a status label with nothing
   that ever computes it.
5. **Nothing proactive.** Every existing feature is pull-based (the user has to ask). `PRD.md §7.3/§8`
   calls for both reactive *and* proactive periodic analysis; only reactive shipped.
6. **No deadline concept.** No due-date field anywhere, no `DEADLINE` node usage, `DUE_BEFORE` was never
   added to the extraction allow-list.
7. **No outbound integration.** Everything built so far only *ingests* GitHub/Slack. Nothing has ever
   posted back to Slack — no bot token usage, no `chat.postMessage`/`conversations.open` calls exist.

## Expanded use cases

Grouped by how a PM/team-lead would actually reach for them:

**Ask, on demand**
- "What's blocking us right now, ranked by how long it's been stuck?"
- "Has this come up before? What did we decide about X last month?" (needs semantic search over full
  history, not just the last 50 rows)
- "What did each person touch yesterday?" (needs sender/author attribution)
- "Which PRs have sat longest without review or merge?"

**Told, without asking**
- **Morning/weekly digest** posted to a Slack channel: what changed, what's newly at risk, what's still
  unresolved from last time.
- **Conflict alert**: the moment a node goes `CONFLICTED`, DM the people whose claims disagree, asking
  them to reconcile — not just surface it in a dashboard someone has to remember to check.
- **Deadline-crossed alert**: DM the assignee (and escalate to the PM if unacknowledged after N hours).
- **Stale-work nudge**: a node with no activity in N days gets a "hey, any update on this?" DM to its
  owner, converting passive Unknown-detection into an active check-in.
- **New-dependency confirmation**: when the system infers an undeclared `BLOCKS`/`DEPENDS_ON` edge from a
  Slack message, ask the PM to confirm it rather than silently trusting an inference for something
  consequential (matches `PRD.md §6` "human confirmation for consequential actions").
- **Escalating conflicts**: a conflict unresolved after N days escalates from "DM the two people involved"
  to "notify the PM directly."
- **Workload rollup**: flag when one person is the blocker on an unusually large number of open items —
  a capacity signal for the PM, not a performance judgment (see guardrail below).

**At a glance**
- The actual `PRD.md §10.1` dashboard: active/blocked/conflicted/unknown counts, the critical dependency
  chain, top risks — one screen, no clicking into tabs.

## Explicit guardrail

`PRD.md §15` lists "an employee-performance monitoring system" as a **non-goal**. Sender attribution and
workload visibility are useful and buildable; a "who's to blame" judgment is not something this product
should compute. Every alert above targets *unresolved work*, never a person's performance — the wording
matters (e.g. "this conflict needs someone's input" rather than "Alex hasn't responded").

## Architecture this actually requires

- **`events` table, for real.** Log every raw inbound webhook payload here at ingestion time, before
  extraction runs — this is the actual full-history record, independent of what extraction manages to
  recognize. Extraction stays as-is on top of it.
- **`actions` table (new).** Every autonomous thing Project Brain does — an alert sent, a digest posted —
  gets a row: what, to whom, when, and (later) whether it was acknowledged. Needed for two things: (1)
  idempotency, so a periodic sweep doesn't re-alert on every run, and (2) the "observe response" half of
  `PRD.md §8`'s agent loop, which nothing currently closes.
- **Sender identity.** Capture `event["user"]` (Slack) and the commit/PR author (GitHub) alongside
  evidence. Cross-platform identity linking (a GitHub login and a Slack user being the same human) is a
  real open question — see below.
- **Embeddings + semantic search.** Generate an embedding per evidence row at write time (Nebius Token
  Factory likely has an embedding-model endpoint alongside Nemotron — needs confirming), store it in the
  already-existing `embedding` column, and add a pgvector similarity query the agent can call instead of
  "last 50 rows."
- **A periodic sweep.** Staleness and deadline checks are triggered by the *absence* of an event, so they
  can't be webhook-driven. Needs a scheduled job — `TechStack.md §2/§14` already names Nebius Serverless
  Jobs for exactly this ("periodic project analysis"), separate from the persistent webhook worker.
- **Outbound Slack client.** `SLACK_BOT_TOKEN` is already in `.env.example` and has never been used.
  Needs `chat.postMessage` (channel digests) and `conversations.open` + `chat.postMessage` (DMs). Also
  needs Project Brain actually installed as a Slack app with a bot user in the workspace — a real setup
  step, not just code.
- **Deadline model.** A due-date field (on the node, or a dedicated `DEADLINE` node type per the original
  PRD enum) plus `DUE_BEFORE` added to the extraction allow-list, plus "crossed" detection logic
  analogous to the existing risk BFS.

## Open product questions (before building alerts specifically)

1. **Decided**: conflict alerts DM both disagreeing parties directly, asking them to reconcile; the PM is
   not routed through by default. (Escalation-to-PM-after-N-days is still open — not yet decided whether
   that ships in Slice 10 or later.)
2. **Decided**: GitHub login → Slack user ID mapping is a manual table for MVP — no automatic inference.
3. What's the re-alert policy so this doesn't become spam? (Once per state change? Daily cap? Escalation
   ladder?) — still open.
4. Does the demo/hackathon scope want the Slack *app* actually installed with a bot user, or is showing
   the alert-sending code path (without a live workspace) enough for the submission? — still open.

## Proposed slices (sequenced by what unlocks what)

| # | Slice | Depends on | Status |
|---|---|---|---|
| 6 | Real event logging (`events` table) + sender/author identity capture | nothing — foundational | **Done** (`bb9cc76`) |
| 7 | Semantic evidence search (embeddings + pgvector query), wired into `/agent/investigate` | 6 | **Done** (`aa452fd`) — also fixed a pre-existing bug: `evidence.embedding` was declared `vector(1536)` since slice 0, a guess never checked against a real model; the real Nebius embedding model (`Qwen/Qwen3-Embedding-8B`) outputs 4096 dims |
| 8 | Staleness/`UNKNOWN` detection + the periodic sweep worker | 6 | Not started |
| 9 | Deadline tracking (`DEADLINE` nodes, `DUE_BEFORE`, crossed-deadline detection) | 6, 8 (reuses the sweep) | Not started |
| 10 | Outbound Slack alerting (`actions` table, bot client, conflict/deadline/staleness alert policies) | 6, 8, 9 | Not started |
| 11 | PM Dashboard view (`PRD.md §10.1`) | 6–9 | Not started |

Not yet scoped in detail — cross-platform identity linking (question 2 above) needs a product decision
before Slice 10 can actually DM the right person for a GitHub-sourced conflict.
