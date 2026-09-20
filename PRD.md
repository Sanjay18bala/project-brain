# Project Brain — Product Requirements Document

## 1. Product Overview

**Project Brain** is an AI agent that continuously reconstructs the real state of a software project from fragmented information across tools such as GitHub and Slack.

Instead of functioning as another task manager, Project Brain maintains an evidence-backed project state graph and continuously analyzes it for blockers, dependencies, conflicting information, unknown or stale states, emerging risks, and downstream impact.

### Core question

> **What is actually happening in this project right now, and what evidence supports that?**

---

## 2. Problem

Software teams distribute project information across many systems:

- GitHub — issues, pull requests, commits, and code activity
- Slack — discussions, decisions, blockers, and informal status updates
- Project-management tools — declared task states and deadlines
- Documents and meetings — requirements and decisions

The problem is not simply lack of information.

The problem is that **project state becomes fragmented, stale, and contradictory**.

Example:

```text
Project tracker:
Authentication → In Progress

GitHub:
Authentication PR → Merged

Slack:
"Still working on authentication."

Frontend:
"Blocked until authentication is finished."
```

A human must manually reconcile these signals.

Project Brain continuously performs that reconciliation.

---

## 3. Vision

Build a continuously evolving **memory and situational-awareness layer for software projects**.

The system observes project activity, turns evidence into structured project state, maintains relationships between entities, and reasons about how changes propagate through the project.

The project graph is the central representation.

```text
Person
  ↓
Task
  ↓
Dependency
  ↓
Issue
  ↓
Milestone
  ↓
Deadline
```

Every important relationship should be backed by evidence.

---

## 4. Product Positioning

Project Brain should **not** be positioned as:

> An AI project manager.

Instead:

> **Project Brain is an evidence-backed project state engine that continuously reconstructs what is actually happening inside a software project.**

Traditional project management asks:

> "What does the project tracker say?"

Project Brain asks:

> "What does the available evidence indicate is actually happening?"

---

## 5. Target Users

### Primary users

Small software and AI teams of approximately 3–10 people.

### Initial use cases

- Hackathon teams
- Startup engineering teams
- Research teams
- Open-source teams
- Distributed engineering teams

The initial MVP should optimize for a small engineering team rather than enterprise-scale project management.

---

## 6. Product Principles

### Evidence over assumptions

Important claims should have supporting evidence.

### Unknown is a valid state

The system should not invent certainty when evidence is insufficient.

Supported state categories:

```text
KNOWN
UNKNOWN
CONFLICTED
```

### Human confirmation for consequential actions

The agent can identify risks and recommend actions, but should not silently modify important commitments.

### Continuous state, not static summaries

The product should maintain project state over time rather than generate one-time reports.

### Explainability

Users should be able to ask:

> "Why do you think this?"

and see the underlying evidence.

---

# 7. Core Features

## 7.1 Project Knowledge Graph

The system maintains a graph containing project entities and relationships.

### Node types

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

### Relationship types

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
Deployment
```

---

## 7.2 Evidence Layer

Every significant relationship or state claim should contain evidence.

Example:

```json
{
  "relationship": "BLOCKS",
  "source": "Authentication",
  "target": "Frontend Integration",
  "confidence": 0.91,
  "evidence": [
    {
      "source": "Slack",
      "reference": "message_284"
    },
    {
      "source": "GitHub",
      "reference": "issue_42"
    }
  ]
}
```

The agent should be able to explain the origin of its conclusions.

---

## 7.3 Continuous Monitoring

Project Brain continuously consumes new project activity.

```text
New Event
    ↓
Extract Information
    ↓
Compare With Existing State
    ↓
Update Graph
    ↓
Analyze Consequences
    ↓
Detect Risks / Conflicts
    ↓
Take Appropriate Action
```

---

## 7.4 Conflict Detection

The system detects contradictions between information sources.

Example:

```text
GitHub:
Authentication → MERGED

Slack:
"Authentication still needs work."

Project Tracker:
Authentication → IN PROGRESS
```

Project Brain produces:

```text
⚠ STATE CONFLICT

Authentication

GitHub: Completed
Slack: Active work
Tracker: In Progress

Confidence: Low

Recommended action:
Confirm current authentication status.
```

The system should not arbitrarily select one source as truth. Instead, each conflicting claim receives a **reconciliation score** based on recency — how recently the claim was made. Source trust is not scored by the system; each claim's evidence (including who reported it) is always shown, so the user can judge source credibility themselves.

The most recent claim is surfaced as the more likely current state, but the conflict is still shown to the user and never silently resolved — this only ranks the evidence, it does not overwrite the record. See TechStack.md §4a for the exact scoring formula.

---

## 7.5 Unknown-State Detection

The system should explicitly represent uncertainty.

Example:

```text
OCR Pipeline

Status: UNKNOWN

Reason:
No recent GitHub activity.
Most recent Slack reference is 3 days old.
Owner appears to have switched tasks.
```

---

## 7.6 Dependency Detection

Project Brain identifies relationships that may not be explicitly recorded.

Example:

Slack:

> "Frontend integration can't start until the OCR output format is finalized."

The system creates:

```text
OCR Output
     │
     │ BLOCKS
     ▼
Frontend Integration
```

The relationship includes the Slack message as evidence.

---

## 7.7 Risk Detection

The system analyzes the project graph for potential downstream consequences.

Example:

```text
OCR
 ↓
Frontend
 ↓
Testing
 ↓
Deployment
```

If OCR becomes uncertain or delayed, Project Brain identifies the potential propagation chain and explains the evidence.

It should distinguish **potential risk** from confirmed failure.

---

## 7.8 "What Changed?"

Users can ask:

> What changed since yesterday?

Project Brain generates a causal timeline.

```text
Sept 17
API work delayed
      ↓
Sept 18
Authentication dependency discovered
      ↓
Sept 18
Developer reassigned to database issue
      ↓
Sept 19
Frontend integration became blocked
      ↓
Current
Testing milestone may be affected
```

---

## 7.9 "Why?"

Users can investigate any important conclusion.

Example:

> Why is deployment at risk?

The agent traces the dependency graph and provides evidence.

```text
Deployment
   ↑
Testing
   ↑
Frontend
   ↑
OCR

Evidence:
Slack message #284
GitHub Issue #183
GitHub PR #190
```

---

## 7.10 "What Don't We Know?"

Users can ask:

> What don't we currently know?

The agent identifies:

- Stale task states
- Missing owners
- Unconfirmed dependencies
- Conflicting information
- Missing deadlines
- Tasks with insufficient evidence

---

# 8. Agent Workflow

The agent follows an observe → reason → act loop.

```text
OBSERVE
   ↓
Extract new information
   ↓
RECONCILE
   ↓
Update project graph
   ↓
REASON
   ↓
Detect dependencies / conflicts / risks
   ↓
DECIDE
   ↓
Determine whether action is warranted
   ↓
ACT
   ↓
Notify / ask / create follow-up
   ↓
OBSERVE RESPONSE
   ↓
Update graph
```

The system supports both reactive event-driven behavior and proactive periodic analysis.

---

# 9. Agent Actions

For the MVP, the agent may:

- Update project state
- Flag a risk
- Identify a blocker
- Detect a conflict
- Ask for clarification
- Send a Slack notification
- Generate a project summary
- Create a follow-up issue when explicitly authorized

The agent should not automatically reassign people, change major deadlines, close issues, or modify critical commitments without human confirmation.

---

# 10. User Interface

## 10.1 Project Dashboard

```text
PROJECT BRAIN

AI Document Processor

17 Active
3 Blocked
2 Conflicted
4 Unknown

────────────────────────

Critical Dependencies

OCR
 ↓
Frontend
 ↓
Testing
 ↓
Deployment

────────────────────────

Detected Risks

⚠ OCR status uncertain
⚠ Frontend dependency unresolved
⚠ Authentication state conflict
```

## 10.2 Project Graph

Users can zoom, pan, select nodes, inspect relationships, inspect evidence, and view state history.

## 10.3 Evidence View

Users can inspect why the system believes a relationship exists.

## 10.4 Agent Interface

Users can ask:

```text
What is blocking us?
Why is deployment at risk?
What changed today?
Who is working on authentication?
What don't we know?
Show me conflicting information.
```

---

# 11. Integrations

## MVP

### GitHub

Use the GitHub API and Webhooks for:

- Issues
- Pull requests
- Commits
- Reviews
- Repository activity

### Slack

Use the Slack API and Events API for:

- Messages
- Threads
- Mentions
- Project discussions
- Blockers
- Decisions

A third project-management integration can be added later if time allows.

---

# 12. AI Requirements

The AI system must support:

### Extraction

People, tasks, issues, deadlines, decisions, dependencies, status changes, and blockers.

### Reconciliation

Compare new information with existing project state.

### Reasoning

Reason across multiple pieces of evidence.

### Uncertainty

Represent confidence and unknown states.

### Explanation

Provide evidence supporting important conclusions.

---

# 13. Technical Architecture

```text
GitHub ─────┐
            │
Slack ──────┤
            ▼
     Event Ingestion
            │
            ▼
     Event Processing
            │
            ▼
      NVIDIA Nemotron
            │
            ▼
    Evidence Extraction
            │
            ▼
      Project State Graph
            │
            ▼
    Agentic Reasoning
     /        |         \
    ↓         ↓          ↓
  Risks   Conflicts   Unknowns
    \         |          /
     \        |         /
            ↓
       Action Layer
            │
            ▼
      Slack / GitHub
```

---

# 14. MVP Scope

### P0 — Required

1. GitHub integration
2. Slack integration
3. Event ingestion
4. NVIDIA Nemotron integration
5. Entity/relationship extraction
6. PostgreSQL project graph
7. Evidence storage
8. Conflict detection
9. Dependency/risk detection
10. React dashboard
11. Agent investigation interface
12. Deployment to Nebius AI Cloud (working, publicly demoable app)

### P1 — Important if time allows

- "What changed?"
- "What don't we know?"
- Automated Slack alerts
- Timeline visualization
- Periodic project analysis

### P2 — Stretch

- Automatic issue creation
- Meeting/document ingestion
- Additional integrations
- Multi-project support
- More advanced predictive analysis

---

# 15. Non-Goals

The MVP will not attempt to become:

- A Jira replacement
- A Linear replacement
- A Slack replacement
- A generic chatbot
- A full enterprise project-management platform
- An employee-performance monitoring system
- A fully autonomous project manager
- A system with dozens of integrations

---

# 16. Hackathon Alignment

Project Brain is intended for the **Best Apps & Agents** track.

The project will satisfy the core requirements by providing:

- A working software application
- Nebius Token Factory and/or Nebius AI Cloud
- At least one NVIDIA open-source model
- A public GitHub repository
- An open-source license
- A working demonstration
- A clear explanation of Nebius and NVIDIA usage

The agent performs a multi-step workflow:

```text
Observe
→ Extract
→ Retrieve
→ Reconcile
→ Update
→ Reason
→ Detect
→ Act
→ Observe again
```

---

# 17. Hackathon Demo

The demo should use a controlled project with intentionally planted events.

### Step 1 — Initial state

Show:

```text
OCR
Frontend
Testing
Deployment
```

with normal project status.

### Step 2 — New Slack information

Send:

> "I'm switching from OCR to database work for now."

Project Brain updates OCR to:

```text
UNKNOWN
```

### Step 3 — Dependency appears

Another Slack message:

> "Frontend can't proceed until OCR output is finalized."

Project Brain creates:

```text
OCR
 ↓ BLOCKS
Frontend
```

### Step 4 — GitHub activity

A GitHub PR provides additional evidence.

### Step 5 — Conflict

Create conflicting information:

```text
GitHub → Authentication merged
Slack → Authentication still being worked on
```

Project Brain flags:

```text
⚠ CONFLICT
```

### Step 6 — User investigation

Ask:

> Why is the deployment at risk?

Project Brain traces:

```text
OCR
 ↓
Frontend
 ↓
Testing
 ↓
Deployment
```

and presents the supporting evidence.

---

# 18. Success Criteria

The MVP is successful if it can demonstrate:

### State reconstruction

Identify project entities and current state from unstructured information.

### Evidence grounding

Trace important conclusions back to source evidence.

### Conflict detection

Identify intentionally contradictory information across GitHub and Slack.

### Dependency reasoning

Infer relationships that are not explicitly represented as task dependencies.

### Risk reasoning

Identify downstream impact from a changing upstream task.

### Continuous operation

Update project state as new events arrive without requiring manual graph maintenance.

### Agentic investigation

Answer project questions by querying the graph and retrieving evidence rather than generating unsupported answers.

---

# 19. Key Product Differentiator

| Traditional PM | Project Brain |
|---|---|
| Tracks declared status | Reconstructs project state |
| User-maintained | Continuously observed |
| Task-centric | Evidence-centric |
| Assumes data is correct | Detects contradictions |
| Shows blockers | Reasons about propagation |
| Stores history | Explains causal changes |
| Answers "what?" | Answers "what, why, and how do we know?" |

---

# 20. One-Sentence Pitch

> **Project Brain is an AI agent that continuously reconstructs the real state of a software project from GitHub, Slack, and other sources, building an evidence-backed project graph that detects hidden dependencies, conflicting information, and emerging risks before the team discovers them manually.**

---

# 21. Product North Star

The long-term goal is not to replace project managers or task-management tools.

The goal is to make project state **machine-readable, continuously updated, explainable, and trustworthy**.

The ideal experience is:

> The team does the work normally. Project Brain watches the evidence, maintains the project's memory, notices when reality diverges from the team's stated plan, and tells the team what changed, why it matters, and what evidence supports that conclusion.
