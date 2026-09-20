# Project Brain

Evidence-backed project state engine. See [`PRD.md`](PRD.md) for product scope and [`TechStack.md`](TechStack.md) for architecture decisions.

## What's built

GitHub + Slack webhooks → Nemotron entity/relationship/state extraction → Postgres graph, with:

- Conflict detection — recency-scored claims when sources disagree (`GET /projects/{id}/conflicts`)
- Dependency/risk detection — BLOCKS/DEPENDS_ON chains propagated from conflicted nodes (`GET /projects/{id}/risks`)
- Agent investigation — free-text Q&A grounded only in the graph/evidence, never unsupported generation (`POST /agent/investigate`)
- A React dashboard with Graph / Conflicts / Risks / Agent tabs

## Local development

```bash
cp .env.example .env   # fill in NEBIUS_API_KEY, GITHUB_WEBHOOK_SECRET, SLACK_SIGNING_SECRET, DATABASE_URL
docker compose up
psql "$DATABASE_URL" -f database/seed/demo_project.sql   # creates the single demo project
```

GitHub and Slack webhooks need a public HTTPS URL — tunnel `POST /events/github` and `POST /events/slack`
with `ngrok` or `smee.io` (see TechStack.md §15). Both routes are authenticated by their own webhook
signature, not `API_KEY` — GitHub/Slack can't attach custom headers to their deliveries. `API_KEY` only
guards `GET /projects/{id}/graph`, called by the frontend.

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
