import { useState } from "react";
import { ConflictView } from "./conflicts/ConflictView";
import { GraphView } from "./graph/GraphView";

const DEMO_PROJECT_ID = import.meta.env.VITE_DEMO_PROJECT_ID ?? "";

export default function App() {
  const [tab, setTab] = useState<"graph" | "conflicts">("graph");

  return (
    <div className="flex h-screen w-full flex-col">
      <div className="flex items-center gap-4 border-b p-2">
        <h1 className="text-lg font-semibold">Project Brain</h1>
        <button
          className={tab === "graph" ? "font-bold underline" : "text-gray-500"}
          onClick={() => setTab("graph")}
        >
          Graph
        </button>
        <button
          className={tab === "conflicts" ? "font-bold underline" : "text-gray-500"}
          onClick={() => setTab("conflicts")}
        >
          Conflicts
        </button>
      </div>
      <div className="flex-1 overflow-hidden">
        {tab === "graph" ? <GraphView projectId={DEMO_PROJECT_ID} /> : <ConflictView projectId={DEMO_PROJECT_ID} />}
      </div>
    </div>
  );
}
