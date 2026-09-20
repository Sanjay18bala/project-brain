-- Node identity is now (project_id, name) instead of (project_id, type, name).
--
-- Discovered via testing: the same real-world entity ("Authentication") gets typed
-- differently across sources (a GitHub PR -> PULL_REQUEST, a Slack message about the
-- same topic -> ISSUE), which under the old (type, name) key created two separate nodes
-- that could never be compared for conflict — each held only one claim, so neither ever
-- looked CONFLICTED even though the sources actively disagreed. Collapsing identity to
-- name alone fixes this at the cost of merging a genuinely different entity that happens
-- to share a name with something else (accepted tradeoff — narrower failure mode).
ALTER TABLE nodes DROP CONSTRAINT nodes_project_id_type_name_key;
ALTER TABLE nodes ADD CONSTRAINT nodes_project_id_name_key UNIQUE (project_id, name);
