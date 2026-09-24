-- Slice 13 (roadmap-v3, task 1): real project creation, and a connections table mapping
-- an external platform identity (a GitHub App installation, for now) to a project.
--
-- projects already exists (0001_init.sql) but nothing has ever inserted into it except
-- database/seed/demo_project.sql - this migration doesn't change that table, just gives
-- it a real API in front of it (see repository.create_project / routes.py POST /projects).

CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    external_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (platform, external_id)
);

-- One external installation (a GitHub App installation id, later a Slack team_id, etc.)
-- maps to exactly one project - installing on the same org twice for two different
-- projects is rejected by this constraint, not silently overwritten.
CREATE INDEX connections_project_id_idx ON connections (project_id);
