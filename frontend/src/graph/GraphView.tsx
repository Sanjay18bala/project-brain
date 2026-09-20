import { useEffect, useState } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { fetchGraph } from "../api/client";

export function GraphView({ projectId }: { projectId: string }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGraph(projectId)
      .then((data) => {
        setNodes(
          data.nodes.map((n, i) => ({
            id: n.id,
            position: { x: (i % 5) * 200, y: Math.floor(i / 5) * 120 },
            data: { label: `${n.name} (${n.status})` },
          })),
        );
        setEdges(
          data.edges.map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            label: e.relationship,
          })),
        );
      })
      .catch((err) => setError(String(err)));
  }, [projectId]);

  if (error) return <div className="p-4 text-red-600">{error}</div>;

  return (
    <div className="h-screen w-full">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
