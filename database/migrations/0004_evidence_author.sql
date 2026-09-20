-- Sender/author identity, captured alongside evidence: a GitHub login (issue/PR author)
-- or a Slack user ID. Needed for roadmap-v2's per-person features (who's blocked, who to
-- alert) — evidence previously had no way to answer "who said/did this."
ALTER TABLE evidence ADD COLUMN author TEXT;
