# Project Brain

Evidence-backed project state engine. See [`PRD.md`](PRD.md) for product scope and [`TechStack.md`](TechStack.md) for architecture decisions.

## Slice 0 — walking skeleton

GitHub webhook → HMAC verification → Nemotron entity/relationship extraction → Postgres graph → React Flow dashboard.

## Local development

```bash
cp .env.example .env   # fill in NEBIUS_API_KEY, GITHUB_WEBHOOK_SECRET, DATABASE_URL
docker compose up
```

GitHub webhooks need a public HTTPS URL — tunnel `POST /events/github` with `ngrok` or `smee.io` (see TechStack.md §15).

Backend tests:

```bash
cd backend && pip install -r requirements.txt && pytest
```
