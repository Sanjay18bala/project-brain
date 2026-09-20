import { GraphView } from "./graph/GraphView";

const DEMO_PROJECT_ID = import.meta.env.VITE_DEMO_PROJECT_ID ?? "";

export default function App() {
  return (
    <div className="flex h-screen w-full flex-col">
      <h1 className="p-2 text-lg font-semibold">Project Brain</h1>
      <GraphView projectId={DEMO_PROJECT_ID} />
    </div>
  );
}
