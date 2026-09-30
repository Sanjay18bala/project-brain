import { useEffect, useState } from "react";
import { AgentChat } from "./agent/AgentChat";
import {
  createProject,
  fetchProjects,
  getGithubInstallUrl,
  getGoogleChatConnectCode,
  getSlackInstallUrl,
  type Project,
} from "./api/client";
import { ConflictView } from "./conflicts/ConflictView";
import { Dashboard } from "./dashboard/Dashboard";
import { GraphView } from "./graph/GraphView";
import { RiskPanel } from "./risks/RiskPanel";

const DEMO_PROJECT_ID = import.meta.env.VITE_DEMO_PROJECT_ID ?? "";

type Tab = "dashboard" | "graph" | "conflicts" | "risks" | "agent";

const TABS: { id: Tab; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "graph", label: "Graph" },
  { id: "conflicts", label: "Conflicts" },
  { id: "risks", label: "Risks" },
  { id: "agent", label: "Agent" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<string>(DEMO_PROJECT_ID);

  useEffect(() => {
    fetchProjects()
      .then((fetched) => {
        setProjects(fetched);
        if (!projectId && fetched.length > 0) setProjectId(fetched[0].id);
      })
      .catch((err) => console.error(err));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleNewProject() {
    const name = window.prompt("Project name");
    if (!name) return;
    const project = await createProject(name);
    setProjects((prev) => [project, ...prev]);
    setProjectId(project.id);
  }

  async function handleConnectGithub() {
    if (!projectId) return;
    const url = await getGithubInstallUrl(projectId);
    window.location.href = url;
  }

  async function handleConnectSlack() {
    if (!projectId) return;
    const url = await getSlackInstallUrl(projectId);
    window.location.href = url;
  }

  async function handleConnectGoogleChat() {
    if (!projectId) return;
    const code = await getGoogleChatConnectCode(projectId);
    window.alert(
      `1. Add the Project Brain bot to your Google Chat space.\n2. In that space, send:\n\nconnect ${code}\n\nThis code expires in 30 minutes.`,
    );
  }

  return (
    <div className="flex h-screen w-full flex-col bg-surface">
      <div className="flex items-center gap-1 border-b border-border bg-panel px-4 py-2 shadow-card">
        <h1 className="mr-4 text-base font-semibold tracking-tight text-ink">Project Brain</h1>
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            className={
              tab === id
                ? "rounded-md bg-accent-subtle px-3 py-1.5 text-sm font-medium text-accent"
                : "rounded-md px-3 py-1.5 text-sm font-medium text-muted hover:bg-surface hover:text-ink"
            }
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <select
            className="rounded-lg border border-border bg-panel px-2.5 py-1.5 text-sm text-ink"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            {projectId && !projects.some((p) => p.id === projectId) && (
              <option value={projectId}>demo project</option>
            )}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button className="btn-secondary" onClick={handleNewProject}>
            New Project
          </button>
          <button className="btn-secondary" onClick={handleConnectGithub} disabled={!projectId}>
            Connect GitHub
          </button>
          <button className="btn-secondary" onClick={handleConnectSlack} disabled={!projectId}>
            Connect Slack
          </button>
          <button className="btn-secondary" onClick={handleConnectGoogleChat} disabled={!projectId}>
            Connect Google Chat
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-hidden">
        {tab === "dashboard" && <Dashboard projectId={projectId} />}
        {tab === "graph" && <GraphView projectId={projectId} />}
        {tab === "conflicts" && <ConflictView projectId={projectId} />}
        {tab === "risks" && <RiskPanel projectId={projectId} />}
        {tab === "agent" && <AgentChat projectId={projectId} />}
      </div>
    </div>
  );
}
