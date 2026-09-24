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
    <div className="flex h-screen w-full flex-col">
      <div className="flex items-center gap-4 border-b p-2">
        <h1 className="text-lg font-semibold">Project Brain</h1>
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            className={tab === id ? "font-bold underline" : "text-gray-500"}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <select
            className="border rounded px-2 py-1"
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
          <button className="border rounded px-2 py-1" onClick={handleNewProject}>
            New Project
          </button>
          <button className="border rounded px-2 py-1" onClick={handleConnectGithub} disabled={!projectId}>
            Connect GitHub
          </button>
          <button className="border rounded px-2 py-1" onClick={handleConnectSlack} disabled={!projectId}>
            Connect Slack
          </button>
          <button className="border rounded px-2 py-1" onClick={handleConnectGoogleChat} disabled={!projectId}>
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
