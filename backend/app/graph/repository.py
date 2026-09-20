from psycopg.types.json import Jsonb


def project_exists(conn, project_id) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM projects WHERE id = %s", (project_id,))
    return cur.fetchone() is not None


def upsert_node(conn, project_id, type_, name, status="KNOWN", metadata=None):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO nodes (project_id, type, name, status, metadata)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (project_id, type, name)
        DO UPDATE SET status = EXCLUDED.status, updated_at = now()
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


def add_evidence(conn, project_id, node_id, source_type, source_ref, content, url, occurred_at):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO evidence (project_id, node_id, source_type, source_ref, content, url, occurred_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (project_id, node_id, source_type, source_ref, content, url, occurred_at),
    )


def lock_node(conn, node_id):
    """Row-locks the node so concurrent writers touching it serialize their conflict recompute.

    # ponytail: per-node FOR UPDATE lock, fine at MVP concurrency; revisit with a queue
    # if webhook volume ever makes lock contention a real bottleneck.
    """
    cur = conn.cursor()
    cur.execute("SELECT id FROM nodes WHERE id = %s FOR UPDATE", (node_id,))


def add_state_change(conn, project_id, node_id, source_type, source_ref, claimed_state, confidence, occurred_at):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO state_changes (project_id, node_id, source_type, source_ref, claimed_state, confidence, occurred_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (project_id, node_id, source_type, source_ref, claimed_state, confidence, occurred_at),
    )


def get_state_changes_for_node(conn, node_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_type, source_ref, claimed_state, confidence, occurred_at
        FROM state_changes WHERE node_id = %s
        ORDER BY occurred_at DESC
        """,
        (node_id,),
    )
    cols = ["source_type", "source_ref", "claimed_state", "confidence", "occurred_at"]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


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
        SELECT n.name, e.source_type, e.source_ref, e.content, e.url, e.occurred_at
        FROM evidence e
        JOIN nodes n ON n.id = e.node_id
        WHERE e.project_id = %s
        ORDER BY e.occurred_at DESC
        LIMIT %s
        """,
        (project_id, limit),
    )
    cols = ["node_name", "source_type", "source_ref", "content", "url", "occurred_at"]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


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
