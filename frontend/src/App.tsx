import { useState } from "react";
import { AgentChat } from "./agent/AgentChat";
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
      </div>
      <div className="flex-1 overflow-hidden">
        {tab === "dashboard" && <Dashboard projectId={DEMO_PROJECT_ID} />}
        {tab === "graph" && <GraphView projectId={DEMO_PROJECT_ID} />}
        {tab === "conflicts" && <ConflictView projectId={DEMO_PROJECT_ID} />}
        {tab === "risks" && <RiskPanel projectId={DEMO_PROJECT_ID} />}
        {tab === "agent" && <AgentChat projectId={DEMO_PROJECT_ID} />}
      </div>
    </div>
  );
}
