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
