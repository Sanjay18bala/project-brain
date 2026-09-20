CREATE TABLE state_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    claimed_state TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX state_changes_node_id_idx ON state_changes (node_id);
