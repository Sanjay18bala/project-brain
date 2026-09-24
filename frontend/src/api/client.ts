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

export type DashboardCounts = { active: number; blocked: number; conflicted: number; unknown: number };
export type CrossedDeadline = { deadline: GraphNode; date: string; affected_tasks: GraphNode[] };
export type DashboardResponse = {
  counts: DashboardCounts;
  risks: Risk[];
  conflicts: Conflict[];
  crossed_deadlines: CrossedDeadline[];
};

export async function fetchDashboard(projectId: string): Promise<DashboardResponse> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/dashboard`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch dashboard: ${res.status}`);
  return res.json();
}

export type Project = { id: string; name: string; created_at: string };

export async function fetchProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE}/projects`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to fetch projects: ${res.status}`);
  const data = await res.json();
  return data.projects;
}

export async function createProject(name: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Failed to create project: ${res.status}`);
  return res.json();
}

export async function getGithubInstallUrl(projectId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/connections/github/install?project_id=${projectId}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to get GitHub install URL: ${res.status}`);
  const data = await res.json();
  return data.install_url;
}

export async function getGoogleChatConnectCode(projectId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/connections/googlechat/code?project_id=${projectId}`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to get Google Chat connect code: ${res.status}`);
  const data = await res.json();
  return data.code;
}

export type InvestigateResponse = { answer: string };

export async function investigate(projectId: string, question: string): Promise<InvestigateResponse> {
  const res = await fetch(`${API_BASE}/agent/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ project_id: projectId, question }),
  });
  if (!res.ok) throw new Error(`Failed to investigate: ${res.status}`);
  return res.json();
}
