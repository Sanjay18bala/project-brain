const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export type GraphNode = { id: string; type: string; name: string; status: string };
export type GraphEdge = { id: string; source: string; target: string; relationship: string };
export type GraphResponse = { nodes: GraphNode[]; edges: GraphEdge[] };

export async function fetchGraph(projectId: string): Promise<GraphResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/graph`);
  if (!res.ok) throw new Error(`Failed to fetch graph: ${res.status}`);
  return res.json();
}
