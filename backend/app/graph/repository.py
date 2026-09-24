import secrets

from psycopg.types.json import Jsonb


def _to_vector_literal(embedding: list[float]) -> str:
    """pgvector's text input format is a bare '[v1,v2,...]' literal, cast via ::vector in
    SQL. Avoids adding the `pgvector` pip package as a dependency for something this small."""
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def project_exists(conn, project_id) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM projects WHERE id = %s", (project_id,))
    return cur.fetchone() is not None


def create_project(conn, name: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (name,))
    return cur.fetchone()[0]


def list_projects(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, name, created_at FROM projects ORDER BY created_at DESC")
    cols = ["id", "name", "created_at"]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def create_connection(conn, project_id, platform: str, external_id: str):
    """Links an external platform identity (a GitHub App installation id, for now) to a
    project. UNIQUE (platform, external_id) on the table means installing the same
    external account on a second project fails loudly rather than silently re-pointing it."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO connections (project_id, platform, external_id) VALUES (%s, %s, %s) RETURNING id",
        (project_id, platform, external_id),
    )
    return cur.fetchone()[0]


def get_project_id_for_installation(conn, external_id: str, platform: str = "github"):
    cur = conn.cursor()
    cur.execute(
        "SELECT project_id FROM connections WHERE platform = %s AND external_id = %s",
        (platform, external_id),
    )
    row = cur.fetchone()
    return row[0] if row else None


def create_connect_code(conn, project_id, platform: str) -> str:
    """Google Chat has no OAuth-install flow we control (a PM adds the bot to a space
    through Google's own UI), so we authenticate the connect request the other way: a
    short-lived single-use code the PM types into the space, matched in the webhook
    handler (docs/roadmap-v3-onboarding.md's GitHub `state` param serves the equivalent
    purpose there)."""
    cur = conn.cursor()
    code = secrets.token_hex(4)
    cur.execute(
        "INSERT INTO connect_codes (code, project_id, platform) VALUES (%s, %s, %s)",
        (code, project_id, platform),
    )
    return code


def consume_connect_code(conn, code: str, platform: str):
    """Single-use, 30-minute expiry — deleting on match is what makes it single-use
    without a separate row lock: only one DELETE can ever match a given primary key."""
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM connect_codes WHERE code = %s AND platform = %s "
        "AND created_at > now() - interval '30 minutes' RETURNING project_id",
        (code, platform),
    )
    row = cur.fetchone()
    return row[0] if row else None


def upsert_node(conn, project_id, type_, name, status="KNOWN", metadata=None):
    """Identity is (project_id, name) — not type — so the same real-world entity typed
    differently across sources (a GitHub PR vs. a Slack topic) still resolves to one node
    instead of splitting into ones that can never be compared for conflict. `type` is
    updated to the latest extraction's value, same as `status`; the append-only
    evidence/state_changes tables remain the actual history, not this snapshot row."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO nodes (project_id, type, name, status, metadata)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (project_id, name)
        DO UPDATE SET type = EXCLUDED.type, status = EXCLUDED.status, updated_at = now()
        RETURNING id
        """,
        (project_id, type_, name, status, Jsonb(metadata or {})),
    )
    return cur.fetchone()[0]


def upsert_edge(conn, project_id, source_id, target_id, relationship, confidence=1.0):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO edges (project_id, source_node_id, target_node_id, relationship, confidence)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (project_id, source_node_id, target_node_id, relationship)
        DO UPDATE SET confidence = EXCLUDED.confidence, updated_at = now()
        RETURNING id
        """,
        (project_id, source_id, target_id, relationship, confidence),
    )
    return cur.fetchone()[0]


def add_evidence(conn, project_id, node_id, source_type, source_ref, content, url, occurred_at, author=None, embedding=None):
    cur = conn.cursor()
    embedding_literal = _to_vector_literal(embedding) if embedding is not None else None
    cur.execute(
        """
        INSERT INTO evidence (project_id, node_id, source_type, source_ref, content, url, occurred_at, author, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
        """,
        (project_id, node_id, source_type, source_ref, content, url, occurred_at, author, embedding_literal),
    )


def log_event(conn, project_id, source, event_type, payload, received_at):
    """Durable raw-event log, independent of what extraction manages to recognize —
    written in its own short-lived connection/transaction so a later extraction failure
    can never roll back the fact that the event was received. See docs/roadmap-v2.md."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO events (project_id, source, event_type, payload, received_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (project_id, source, event_type, Jsonb(payload), received_at),
    )
    return cur.fetchone()[0]


def lock_node(conn, node_id):
    """Row-locks the node so concurrent writers touching it serialize their conflict recompute.

    # ponytail: per-node FOR UPDATE lock, fine at MVP concurrency; revisit with a queue
    # if webhook volume ever makes lock contention a real bottleneck.
    """
    cur = conn.cursor()
    cur.execute("SELECT id FROM nodes WHERE id = %s FOR UPDATE", (node_id,))


def add_state_change(conn, project_id, node_id, source_type, source_ref, claimed_state, confidence, occurred_at, author=None):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO state_changes (project_id, node_id, source_type, source_ref, claimed_state, confidence, occurred_at, author)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (project_id, node_id, source_type, source_ref, claimed_state, confidence, occurred_at, author),
    )


def get_state_changes_for_node(conn, node_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_type, source_ref, claimed_state, confidence, occurred_at, author
        FROM state_changes WHERE node_id = %s
        ORDER BY occurred_at DESC
        """,
        (node_id,),
    )
    cols = ["source_type", "source_ref", "claimed_state", "confidence", "occurred_at", "author"]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def get_identity_links(conn, project_id) -> dict:
    """{github_login: slack_user_id} for the project — see app.agents.alerts.resolve_slack_recipient."""
    cur = conn.cursor()
    cur.execute("SELECT github_login, slack_user_id FROM identity_links WHERE project_id = %s", (project_id,))
    return dict(cur.fetchall())


def has_action_been_taken(conn, project_id, node_id, action_type, recipient) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM actions WHERE project_id = %s AND node_id = %s AND action_type = %s AND recipient = %s",
        (project_id, node_id, action_type, recipient),
    )
    return cur.fetchone() is not None


def record_action(conn, project_id, node_id, action_type, recipient, detail=None):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO actions (project_id, node_id, action_type, recipient, detail)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (project_id, node_id, action_type, recipient) DO NOTHING
        """,
        (project_id, node_id, action_type, recipient, detail),
    )


def set_node_status(conn, node_id, status):
    cur = conn.cursor()
    cur.execute("UPDATE nodes SET status = %s, updated_at = now() WHERE id = %s", (status, node_id))


def get_conflicted_nodes(conn, project_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, type, name, status FROM nodes WHERE project_id = %s AND status = 'CONFLICTED'",
        (project_id,),
    )
    cols = ["id", "type", "name", "status"]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


DEFAULT_EVIDENCE_LIMIT = 50


def get_evidence_for_project(conn, project_id, limit=DEFAULT_EVIDENCE_LIMIT):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.id, n.name, e.source_type, e.source_ref, e.content, e.url, e.occurred_at, e.author
        FROM evidence e
        JOIN nodes n ON n.id = e.node_id
        WHERE e.project_id = %s
        ORDER BY e.occurred_at DESC
        LIMIT %s
        """,
        (project_id, limit),
    )
    cols = ["id", "node_name", "source_type", "source_ref", "content", "url", "occurred_at", "author"]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def search_evidence_by_similarity(conn, project_id, query_embedding, limit=25):
    """Cosine-similarity search over evidence with a non-NULL embedding. Rows written
    before this slice (or where the embedding call failed at write time) have a NULL
    embedding and are excluded — they're still findable via get_evidence_for_project."""
    cur = conn.cursor()
    embedding_literal = _to_vector_literal(query_embedding)
    cur.execute(
        """
        SELECT e.id, n.name, e.source_type, e.source_ref, e.content, e.url, e.occurred_at, e.author,
               1 - (e.embedding <=> %s::vector) AS similarity
        FROM evidence e
        JOIN nodes n ON n.id = e.node_id
        WHERE e.project_id = %s AND e.embedding IS NOT NULL
        ORDER BY e.embedding <=> %s::vector
        LIMIT %s
        """,
        (embedding_literal, project_id, embedding_literal, limit),
    )
    cols = ["id", "node_name", "source_type", "source_ref", "content", "url", "occurred_at", "author", "similarity"]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def get_node_last_activity(conn, project_id):
    """For every node in the project, its status and most recent evidence.occurred_at —
    input to the staleness sweep (app.agents.staleness.find_stale_nodes)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT n.id, n.status, MAX(e.occurred_at) AS last_activity
        FROM nodes n
        LEFT JOIN evidence e ON e.node_id = n.id
        WHERE n.project_id = %s
        GROUP BY n.id, n.status
        """,
        (project_id,),
    )
    cols = ["id", "status", "last_activity"]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def mark_nodes_unknown(conn, node_ids):
    if not node_ids:
        return
    cur = conn.cursor()
    cur.execute("UPDATE nodes SET status = 'UNKNOWN', updated_at = now() WHERE id = ANY(%s)", (node_ids,))


def get_graph(conn, project_id):
    cur = conn.cursor()
    cur.execute("SELECT id, type, name, status, metadata FROM nodes WHERE project_id = %s", (project_id,))
    nodes = [dict(zip(["id", "type", "name", "status", "metadata"], row, strict=True)) for row in cur.fetchall()]

    cur.execute(
        "SELECT id, source_node_id, target_node_id, relationship, confidence FROM edges WHERE project_id = %s",
        (project_id,),
    )
    edges = [
        dict(zip(["id", "source", "target", "relationship", "confidence"], row, strict=True))
        for row in cur.fetchall()
    ]
    return {"nodes": nodes, "edges": edges}
