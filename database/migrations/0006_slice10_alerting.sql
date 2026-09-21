-- Slice 10: outbound Slack alerting.

-- Every autonomous action Project Brain takes (an alert sent) gets a row here - the
-- UNIQUE constraint backs the "once per conflict, ever" re-alert policy at the DB level,
-- not just in application code, and gives an audit trail (PRD.md §8's "observe response"
-- loop, once something reads it back).
CREATE TABLE actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    node_id UUID REFERENCES nodes(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    recipient TEXT NOT NULL,
    detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, node_id, action_type, recipient)
);

-- Manual GitHub-login -> Slack-user-id mapping (docs/roadmap-v2.md decision: no automatic
-- cross-platform identity inference for MVP — populate via database/seed/identity_links_example.sql).
CREATE TABLE identity_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    github_login TEXT NOT NULL,
    slack_user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, github_login)
);

-- state_changes never captured who made the claim - evidence.author (slice 6) did, but
-- conflict alerts need to know who to DM per claim, not just per evidence row.
ALTER TABLE state_changes ADD COLUMN author TEXT;
