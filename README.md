# Project Brain

Evidence-backed project state engine. See [`PRD.md`](PRD.md) for product scope and [`TechStack.md`](TechStack.md) for architecture decisions.

## What's built

GitHub + Slack + Google Chat → Nemotron entity/relationship/state/deadline extraction → Postgres graph
(nodes/edges/evidence/state_changes, plus a full raw `events` log independent of what extraction
recognizes), with:

- Conflict detection — recency-scored claims when sources disagree, DMs both parties on Slack once
  ever per conflict (`GET /projects/{id}/conflicts`)
- Dependency/risk detection — BLOCKS/DEPENDS_ON chains propagated from conflicted nodes
  (`GET /projects/{id}/risks`)
- Staleness detection — a periodic sweep marks a quiet `KNOWN` node `UNKNOWN`, reverses automatically the
  next time it's touched by a real event
- Deadline tracking — `DEADLINE` nodes/`DUE_BEFORE` edges, flags dates that have passed
  (`GET /projects/{id}/deadlines`)
- Agent investigation — free-text Q&A grounded in the graph, semantic-searched evidence, and current
  conflicts/risks/deadlines, never unsupported generation (`POST /agent/investigate`)
- A React dashboard (default landing view) plus Graph / Conflicts / Risks / Agent tabs

See [`docs/roadmap-v2.md`](docs/roadmap-v2.md) for the full slice-by-slice history and what's still open.

## Local development

```bash
cp .env.example .env   # fill in NEBIUS_API_KEY, GITHUB_WEBHOOK_SECRET, SLACK_SIGNING_SECRET, DATABASE_URL
docker compose up
psql "$DATABASE_URL" -f database/seed/demo_project.sql   # creates the single demo project
```

GitHub, Slack, and Google Chat all need a public HTTPS URL to deliver events to — tunnel
`POST /events/github`, `POST /events/slack`, and `POST /events/googlechat` with `ngrok` or `smee.io`
(see TechStack.md §15). All three routes are authenticated by their own request signature/bearer token,
not `API_KEY` — none of them can attach custom headers to their deliveries. `API_KEY` only guards the
first-party `GET`/`POST` routes the frontend and agent chat call.

### GitHub setup

GitHub connects via a real [GitHub App](https://github.com/settings/apps/new) with "Request user
authorization (OAuth) during installation" enabled, not a plain per-repo webhook:

1. Create the App: Webhook URL → your public `POST /events/github`; Webhook secret → the same
   `GITHUB_WEBHOOK_SECRET` in `.env`; permissions → Issues (Read), Pull requests (Read); subscribe to
   Issues + Pull request events; **check "Request user authorization (OAuth) during installation"** — this
   is what makes the install callback include a `code`, which is what proves the installer actually owns
   it (a bare `installation_id` alone is spoofable, per GitHub's own docs).
2. Set the Callback URL to your public `GET /connections/github/callback`.
3. Copy the Client ID/Client secret into `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET`, and the app's slug
   (from its settings URL) into `GITHUB_APP_SLUG`.
4. In the UI, select a project and click **Connect GitHub** — it fetches the install URL from
   `GET /connections/github/install`, redirects to GitHub's install screen, and GitHub's callback binds
   the chosen installation to that project. Installations with no connection are ignored (not routed to the
   demo project), so an uninstalled/unmapped installation's events never bleed into someone else's data.

### Slack setup

Slack connects via a standard "Add to Slack" OAuth flow:

1. Create an app at [api.slack.com/apps](https://api.slack.com/apps). Under **OAuth & Permissions**, add
   Bot Token Scopes: `chat:write`, `im:write`, `channels:history`, `groups:history`, `im:history`,
   `mpim:history` — and add a Redirect URL matching your public `GET /connections/slack/callback` exactly.
2. Under **Event Subscriptions**, enable events, set the Request URL to your public `POST /events/slack`
   (Slack's `url_verification` handshake must succeed here), and subscribe to bot events: `message.channels`,
   `message.groups`, `message.im`, `message.mpim`.
3. Copy the Client ID/Client secret from **Basic Information** into `SLACK_CLIENT_ID`/`SLACK_CLIENT_SECRET`,
   and the exact redirect URL into `SLACK_REDIRECT_URI`.
4. In the UI, select a project and click **Connect Slack** — same OAuth-redirect pattern as GitHub. Unlike
   GitHub's installation_id, Slack's `code`→token exchange response directly returns the authorizing
   team's id, so no separate ownership check is needed (the code can only be redeemed for the team that
   completed Slack's consent screen). Teams with no connection are ignored the same way unmapped GitHub
   installations are.

### Google Chat setup

Unlike GitHub (HMAC) and Slack (`v0=` signing), Google Chat verifies with a Google-signed OIDC bearer
token, checked via the `google-auth` library against Google's public keys — not a shared secret you
configure. To wire up a real Google Chat app:

1. Create a Chat app in [Google Cloud Console](https://console.cloud.google.com/apis/library/chat.googleapis.com)
   (APIs & Services → Google Chat API → Configuration), set its connection type to **HTTP endpoint URL**,
   and point that URL at your public `POST /events/googlechat` (via a tunnel for local dev).
2. Set `GOOGLE_CHAT_AUDIENCE` to that exact same URL — it's the expected `audience` claim on the bearer
   token Google sends, not a secret to keep private.
3. Add the app to a space.
4. In the Project Brain UI, select the project and click **Connect Google Chat** — this calls the
   authenticated `POST /connections/googlechat/code` route and shows a short single-use code (30-minute
   expiry). Google Chat has no OAuth-install redirect the way GitHub Apps do, so the connect flow runs in
   reverse: type `connect <code>` as a message in the space you just added the app to. The webhook handler
   matches the code, binds that space to the selected project in the `connections` table, and confirms with
   a reply in the space. From then on, messages in that space flow into that project's extraction pipeline;
   spaces with no connection fall back to the single demo project (`DEFAULT_PROJECT_ID`).

We couldn't test a real signed request locally the way we did for GitHub/Slack (there's no way to
self-sign a token Google's verifier will accept) — `backend/app/ingestion/googlechat.py`'s tests
monkeypatch the verification library instead. The 401 auth boundary itself is confirmed working; the
"accept a real token" path needs an actual Google Chat app pointed at a running instance to verify live.

Backend tests:

```bash
cd backend && pip install -r requirements.txt && pytest
```

## Deployment (Nebius AI Cloud)

The AI layer runs on Nebius Token Factory; the app itself runs on Nebius AI Cloud (see TechStack.md §4/§14).

1. **Token Factory**: get an API key from [Nebius Token Factory](https://tokenfactory.nebius.com/) and set
   `NEBIUS_API_KEY` — no separate provisioning needed, `NEMOTRON_MODEL` already defaults to
   `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` via its OpenAI-compatible endpoint.
2. **Database**: provision a managed PostgreSQL instance (with the `vector` extension available) on Nebius
   AI Cloud, or run the `postgres` service from `docker-compose.yml` on a Nebius Compute VM. Point
   `DATABASE_URL` at it and apply `database/migrations/*.sql` in order, then
   `database/seed/demo_project.sql`.
3. **Backend**: deploy the `backend/Dockerfile` image as a long-running Nebius AI Cloud service (not a
   Serverless Job — see TechStack.md §2/§14, webhook ingestion needs a persistent process, not a batch
   task). Point GitHub's and Slack's webhook config at its public URL for `/events/github` and
   `/events/slack`.
4. **Frontend**: deploy the `frontend/Dockerfile` image (or a static build via `npm run build`) as a second
   Nebius AI Cloud service, with `VITE_API_BASE` pointing at the deployed backend's public URL.
5. Set `API_KEY` (backend) and the matching `VITE_API_KEY` (frontend) to the same real secret — not the
   placeholder in `.env.example`.

## License

[MIT](LICENSE)
