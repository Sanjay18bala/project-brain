-- evidence.embedding was declared vector(1536) in 0001_init.sql as a guess, made before
-- any embedding model was actually wired up. Confirmed live against Nebius Token Factory:
-- Qwen/Qwen3-Embedding-8B outputs 4096-dimensional vectors. Safe to ALTER TYPE directly —
-- every existing row's embedding is still NULL, since nothing has ever written one.
ALTER TABLE evidence ALTER COLUMN embedding TYPE vector(4096);
