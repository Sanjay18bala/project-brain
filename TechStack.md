# Project Brain — Tech Stack

## 1. Overview

Project Brain is an evidence-backed, continuously monitored project intelligence agent.

It ingests project activity from sources such as GitHub and Slack, extracts project entities and relationships using NVIDIA Nemotron through Nebius, maintains a project state graph, detects conflicts/blockers/risks, and provides evidence-backed explanations.

---

## 2. Core Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React + TypeScript | Web application UI |
| Styling | Tailwind CSS | UI styling |
| Graph Visualization | React Flow | Interactive project graph |
| Backend | Python + FastAPI | API and application backend |
| AI Model | NVIDIA Nemotron | Extraction, reconciliation, reasoning |
| AI Infrastructure | Nebius Token Factory | Model inference |
| Database | PostgreSQL | Persistent application/project data |
| Vector Search | pgvector | Semantic evidence retrieval |
| Graph Storage | PostgreSQL | Nodes, edges, relationships, evidence |
| GitHub | GitHub API + Webhooks | Code/project activity ingestion |
| Slack | Slack API + Events API | Team communication ingestion |
| Background Processing | Persistent async worker (queue consumer) on Nebius AI Cloud for continuous event processing; Nebius Serverless Jobs for batch/periodic project analysis only | Event processing |
| Deployment | Nebius AI Cloud | Application/backend infrastructure |
| Source Control | GitHub | Code repository and collaboration |
| Containerization | Docker | Reproducible development/deployment |

---

## 3. Architecture

```text
                         ┌──────────────────┐
                         │      GitHub      │
                         │ Issues / PRs     │
                         │ Commits / Events │
                         └────────┬─────────┘
                                  │
                                  │
                         ┌────────▼─────────┐
                         │      Slack       │
                         │ Messages / Events│
                         └────────┬─────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   Event Ingestion    │
                       │      FastAPI         │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   Event Processing   │
                       │ Async Workers / Jobs │
                       └──────────┬───────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │      NVIDIA Nemotron       │
                    │        via Nebius          │
                    │                            │
                    │ • Entity extraction        │
                    │ • Relationship extraction  │
                    │ • State reconciliation     │
                    │ • Reasoning                │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │       PostgreSQL            │
                    │                            │
                    │ • Project nodes             │
                    │ • Graph edges               │
                    │ • Evidence                  │
                    │ • Events                    │
                    │ • Project state             │
                    │ • pgvector embeddings       │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │     Project Brain Agent    │
                    │                            │
                    │ • Conflict detection       │
                    │ • Blocker detection        │
                    │ • Dependency reasoning     │
                    │ • Risk analysis             │
                    │ • Investigation             │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │      FastAPI API     │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ React + TypeScript   │
                       │                      │
                       │ • Dashboard          │
                       │ • Project Graph      │
                       │ • Evidence           │
                       │ • Risk Panel         │
                       │ • Agent Chat         │
                       └──────────────────────┘
```

---

## 4. AI / Agent Layer

### NVIDIA Nemotron

Nemotron is the primary AI model used by Project Brain.

**Model**: Nemotron 3 Nano 30B A3B (MoE, compute-efficient), served via Nebius Token Factory's OpenAI-compatible API (`https://api.tokenfactory.nebius.com/v1/`). Chosen over Nemotron 3 Super because the reactive per-event pipeline (§7.3 of the PRD) needs low-latency, serverless inference rather than a dedicated GPU endpoint. Nemotron 3 Super remains an option for a periodic/batch deep-analysis job if latency budget allows.

The model will be responsible for:

1. Extracting entities from unstructured project information.
2. Extracting relationships between entities.
3. Determining project-state changes.
4. Reconciling new evidence with existing state.
5. Identifying contradictions.
6. Reasoning over project dependencies.
7. Investigating project risks.
8. Generating evidence-backed explanations.

The application should use structured outputs wherever possible.

Example:

```json
{
  "entities": [
    {
      "type": "TASK",
      "name": "OCR Pipeline"
    },
    {
      "type": "PERSON",
      "name": "Alex"
    }
  ],
  "relationships": [
    {
      "source": "OCR Pipeline",
      "relation": "ASSIGNED_TO",
      "target": "Alex"
    }
  ],
  "state_changes": [
    {
      "entity": "OCR Pipeline",
      "new_state": "UNKNOWN",
      "confidence": 0.72
    }
  ]
}
```

---

## 4a. Conflict Reconciliation Scoring

When two or more sources make conflicting claims about the same entity's state, each claim gets a reconciliation score instead of one source being picked as truth:

```text
score = recency_score(timestamp)
```

`recency_score(timestamp)` — exponential decay, e.g. `exp(-Δt / half_life)`, so a message from minutes ago scores near 1.0 and one from weeks ago decays toward 0.

Source trust (e.g. who reported it) is deliberately not scored. Each claim's evidence — including its author — is always shown alongside the conflict (§9), so the human reviewing it can weigh source credibility themselves rather than the system encoding a role hierarchy.

The higher-scored (more recent) claim is surfaced as the current best estimate, but per PRD §6 ("human confirmation for consequential actions") this only ranks evidence for display — it never silently overwrites the conflicting record. The state remains `CONFLICTED` until a human confirms it.

---

## 5. Agent Workflow

Project Brain follows an observation → reasoning → action loop.

```text
Observe
   ↓
Extract
   ↓
Retrieve Evidence
   ↓
Update Project Graph
   ↓
Reconcile State
   ↓
Detect Conflicts
   ↓
Analyze Dependencies
   ↓
Detect Risks
   ↓
Decide Whether Action Is Needed
   ↓
Notify / Ask / Create Action
   ↓
Observe New Evidence
```

The system should maintain uncertainty instead of forcing every piece of information into a known state.

Supported states:

```text
KNOWN
UNKNOWN
CONFLICTED
```

---

## 6. Database

### PostgreSQL

PostgreSQL will be the primary persistent data store.

Core tables:

```text
projects
users
nodes
edges
evidence
events
state_changes
risks
actions
```

### Example Node

```text
nodes

id
project_id
type
name
status
metadata
created_at
updated_at
```

### Example Edge

```text
edges

id
project_id
source_node_id
target_node_id
relationship
confidence
created_at
updated_at
```

### Example Evidence

```text
evidence

id
source_type
source_id
content
timestamp
url
metadata
embedding
```

---

## 7. Vector Search

### pgvector

pgvector will be used for semantic retrieval of supporting evidence.

Potential evidence sources:

- Slack messages
- GitHub issues
- Pull requests
- Commit messages
- Project documents
- Meeting notes

Important design principle:

> Vector search retrieves evidence; the project graph represents project state.

Project Brain should not become a generic RAG chatbot.

---

## 8. Graph Model

The project graph will initially be implemented using PostgreSQL nodes and edges rather than introducing a dedicated graph database.

### Node Types

```text
PERSON
TASK
ISSUE
MILESTONE
DEADLINE
DECISION
REPOSITORY
PULL_REQUEST
DOCUMENT
MEETING
```

### Relationship Types

```text
ASSIGNED_TO
DEPENDS_ON
BLOCKS
RELATED_TO
MENTIONED_IN
DECIDED_IN
AFFECTS
DUE_BEFORE
CREATED_BY
RESOLVED_BY
CONFLICTS_WITH
```

Example:

```text
Authentication
      │
      │ BLOCKS
      ▼
Frontend Integration
      │
      │ DEPENDS_ON
      ▼
Testing
      │
      │ DUE_BEFORE
      ▼
Deployment Deadline
```

---

## 9. Evidence Model

Every important project-state claim should be traceable to evidence.

Example:

```json
{
  "relationship": "BLOCKS",
  "source": "OCR Pipeline",
  "target": "Frontend Integration",
  "confidence": 0.91,
  "evidence": [
    {
      "source": "slack",
      "reference": "message_284",
      "timestamp": "2026-09-17T14:32:00Z"
    },
    {
      "source": "github",
      "reference": "issue_42"
    }
  ]
}
```

The agent should be able to answer:

> Why do you believe this?

with the underlying evidence.

---

## 10. GitHub Integration

Use:

- GitHub REST API
- GitHub Webhooks
- GitHub OAuth/App authentication

Relevant events:

```text
issues.opened
issues.edited
issues.closed

pull_request.opened
pull_request.closed
pull_request.merged
pull_request.review_submitted

push
```

Flow:

```text
GitHub Event
     ↓
Webhook
     ↓
FastAPI
     ↓
Event Queue
     ↓
AI Processing
     ↓
Graph Update
```

---

## 11. Slack Integration

Use:

- Slack Web API
- Slack Events API
- Slack OAuth

Potential events/data:

```text
messages
mentions
threads
channels
reactions
```

The system should focus on project-relevant information rather than attempting to process every Slack message.

Example:

```text
"I'm blocked because the API isn't ready."

          ↓

Person: Alex
Task: Frontend Integration
State: BLOCKED
Blocker: API
Evidence: Slack message
```

---

## 12. Backend

### FastAPI

FastAPI will expose endpoints such as:

```text
GET  /projects
GET  /projects/{id}
GET  /projects/{id}/graph
GET  /projects/{id}/risks
GET  /projects/{id}/conflicts
GET  /projects/{id}/evidence

POST /events/github
POST /events/slack

POST /agent/investigate
POST /agent/query
POST /agent/actions
```

The backend is responsible for:

- Authentication
- API routing
- Event ingestion, including verifying the GitHub webhook HMAC signature (`GITHUB_WEBHOOK_SECRET`) and the Slack request signing secret on every inbound webhook before processing it
- Graph operations
- Agent orchestration
- Evidence retrieval
- Database access

---

## 13. Frontend

### React + TypeScript

Main views:

```text
Dashboard
Project Graph
Risk View
Conflict View
Evidence View
Agent Chat
Timeline
```

### React Flow

Used for:

```text
Person
  ↓
Task
  ↓
Dependency
  ↓
Task
  ↓
Milestone
```

Users should be able to click nodes and inspect:

- Current state
- Owner
- Dependencies
- Related issues
- Evidence
- Confidence
- State history

---

## 14. Deployment

### Nebius

Primary AI infrastructure:

```text
Nebius
├── Token Factory
│     └── NVIDIA Nemotron
│
└── AI Cloud
      ├── Application backend
      ├── Background processing
      └── Supporting infrastructure
```

Where appropriate, use Nebius Serverless Jobs or equivalent background compute for asynchronous processing and periodic project analysis.

---

## 15. Local Development

Recommended local setup:

```text
Docker
├── frontend
├── backend
└── postgres
```

GitHub and Slack deliver webhooks to a public HTTPS URL, so local development needs a tunnel (e.g. `ngrok` or `smee.io`) forwarding to the backend's `/events/github` and `/events/slack` endpoints.

Environment:

```text
.env

NEBIUS_API_KEY=
NEBIUS_BASE_URL=

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_WEBHOOK_SECRET=

SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_BOT_TOKEN=

DATABASE_URL=
```

Secrets must never be committed to GitHub.

---

## 16. Repository Structure

Recommended structure:

```text
project-brain/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── graph/
│   │   └── api/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── graph/
│   │   ├── ingestion/
│   │   ├── evidence/
│   │   ├── models/
│   │   └── services/
│   ├── tests/
│   └── requirements.txt
│
├── database/
│   ├── migrations/
│   └── seed/
│
├── docs/
│
├── docker-compose.yml
├── README.md
└── .env.example
```

---

## 17. Initial MVP

The first implementation should focus on:

```text
1. GitHub integration
2. Slack integration
3. Event ingestion
4. Nemotron extraction
5. PostgreSQL project graph
6. Evidence storage
7. Conflict detection
8. Dependency/risk detection
9. Evidence-backed agent responses
10. React dashboard
```

Do not initially build:

```text
- Full Jira replacement
- Dozens of integrations
- Automatic task reassignment
- Complex enterprise permissions
- Fully autonomous project management
- Dedicated graph database
```

---

## 18. Core Technical Differentiator

Project Brain should not be positioned as:

> "An AI project manager."

The technical positioning is:

> **An evidence-backed project state engine that continuously reconstructs what is actually happening inside a software project.**

The key architecture is:

```text
Fragmented Project Data
          ↓
      AI Extraction
          ↓
     Evidence Layer
          ↓
    Project State Graph
          ↓
 State Reconciliation
          ↓
Conflict / Dependency / Risk Detection
          ↓
    Agentic Investigation
          ↓
 Evidence-backed Action
```

---

## 19. Hackathon-Specific Requirements

The implementation must satisfy the Nebius × NVIDIA Global AI Hackathon requirements:

- Working software application
- Use Nebius Token Factory or Nebius AI Cloud
- Use at least one NVIDIA open-source model
- Public GitHub repository
- Open-source license
- Working demo
- ≤3-minute demonstration video
- Clear explanation of how Nebius and NVIDIA technology are used

The NVIDIA model and Nebius deployment configuration are Nemotron 3 Nano 30B A3B on Nebius Token Factory (see §4), with continuous event processing running as a persistent worker on Nebius AI Cloud rather than a Serverless Job (see §2).
