const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

function authHeaders(): HeadersInit {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

export type GraphNode = { id: string; type: string; name: string; status: string };
export type GraphEdge = { id: string; source: string; target: string; relationship: string };
export type GraphResponse = { nodes: GraphNode[]; edges: GraphEdge[] };

export async function fetchGraph(projectId: string): Promise<GraphResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/graph`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch graph: ${res.status}`);
  return res.json();
}

export type Claim = {
  source_type: string;
  source_ref: string;
  claimed_state: string;
  confidence: number;
  occurred_at: string;
  score: number;
};
export type Conflict = { node: { id: string; type: string; name: string; status: string }; claims: Claim[] };
export type ConflictsResponse = { conflicts: Conflict[] };

export async function fetchConflicts(projectId: string): Promise<ConflictsResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/conflicts`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch conflicts: ${res.status}`);
  return res.json();
}

export type RiskChainStep = { edge: GraphEdge; node: GraphNode | null };
export type Risk = { source_node: GraphNode; chain: RiskChainStep[] };
export type RisksResponse = { risks: Risk[] };

export async function fetchRisks(projectId: string): Promise<RisksResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/risks`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch risks: ${res.status}`);
  return res.json();
}
