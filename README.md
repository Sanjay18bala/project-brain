# Project Brain

Evidence-backed project state engine. See [`PRD.md`](PRD.md) for product scope and [`TechStack.md`](TechStack.md) for architecture decisions.

## Slice 0 — walking skeleton

GitHub webhook → HMAC verification → Nemotron entity/relationship extraction → Postgres graph → React Flow dashboard.

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
