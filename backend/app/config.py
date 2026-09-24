import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")

# GitHub App (roadmap-v3): OAuth-during-installation lets us verify who actually installed
# the app before trusting an installation_id, which GitHub's own docs warn is otherwise
# spoofable. See docs/roadmap-v3-onboarding.md.
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_APP_SLUG = os.getenv("GITHUB_APP_SLUG", "")

# The public URL Google Chat sends requests to (e.g. https://your-domain.com/events/googlechat).
# Used as the expected audience when verifying Google's signed bearer token — see
# app/ingestion/googlechat.py. Not a shared secret like GITHUB_WEBHOOK_SECRET/
# SLACK_SIGNING_SECRET; Google Chat's request verification works differently (a
# Google-signed OIDC token, not HMAC).
GOOGLE_CHAT_AUDIENCE = os.getenv("GOOGLE_CHAT_AUDIENCE", "")
API_KEY = os.getenv("API_KEY", "")
DEFAULT_PROJECT_ID = os.getenv("DEFAULT_PROJECT_ID", "")

# Origins allowed to call the API from a browser (comma-separated). The frontend sends a
# custom X-API-Key header, which forces the browser to preflight with OPTIONS first.
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]

# Recency-decay time constant for conflict scoring (TechStack.md §4a). No "right" default —
# tune against real usage; a fast-moving team may want minutes, not hours.
RECENCY_HALF_LIFE_SECONDS = float(os.getenv("RECENCY_HALF_LIFE_SECONDS", str(24 * 60 * 60)))

# How long a KNOWN node can go without new evidence before the periodic sweep marks it
# UNKNOWN (PRD.md §7.5). Matches PRD's illustrative "3 days old" example as the default.
STALENESS_THRESHOLD_DAYS = float(os.getenv("STALENESS_THRESHOLD_DAYS", "3"))

# How often the in-process staleness sweep runs. Default 1 hour.
STALENESS_SWEEP_INTERVAL_SECONDS = float(os.getenv("STALENESS_SWEEP_INTERVAL_SECONDS", str(60 * 60)))

# Bot token for outbound Slack messages (chat:write + im:write scopes). Distinct from
# SLACK_SIGNING_SECRET, which only verifies inbound webhook requests.
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
