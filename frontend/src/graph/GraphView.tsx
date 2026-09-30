import { useEffect, useState } from "react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { fetchGraph, type GraphEdge, type GraphNode } from "../api/client";
import { classifyNode, STATUS_BADGE_CLASS } from "../lib/nodeStatus";

const COLUMN_WIDTH = 260;
const ROW_HEIGHT = 92;
const HEADER_HEIGHT = 72;
const UNASSIGNED_LABEL = "Unassigned";

function nodeLabel(node: GraphNode, edges: GraphEdge[]) {
  const bucket = classifyNode(node, edges);
  return (
    <div className="w-full">
      <div className="truncate text-sm font-medium text-ink">{node.name}</div>
      <div className="mt-1 flex items-center gap-1.5 text-[11px] text-muted">
        <span>{node.type}</span>
        <span className={STATUS_BADGE_CLASS[bucket]}>{node.status}</span>
      </div>
    </div>
  );
}

function branchHeaderLabel(node: GraphNode) {
  const isDefault = node.metadata?.is_default === true;
  return (
    <div className="w-full text-center">
      <div className="text-xs font-semibold uppercase tracking-wide text-accent">{isDefault ? "Main branch" : "Branch"}</div>
      <div className="mt-0.5 truncate font-mono text-sm font-semibold text-ink">{node.name}</div>
    </div>
  );
}

/** Groups nodes into swimlanes by which branch's PR they're connected to (via ON_BRANCH
 * and its PR's other 1-hop neighbors), so a PM can see what each branch is actually
 * working on at a glance instead of a flat, ungrouped entity soup. */
function layoutByBranch(nodes: GraphNode[], edges: GraphEdge[]): { nodes: Node[]; edges: Edge[] } {
  const branches = nodes
    .filter((n) => n.type === "BRANCH")
    .sort((a, b) => {
      const aDefault = a.metadata?.is_default === true;
      const bDefault = b.metadata?.is_default === true;
      if (aDefault !== bDefault) return aDefault ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  const columnOf = new Map<string, number>();
  branches.forEach((b, i) => columnOf.set(b.id, i));
  const unassignedColumn = branches.length;

  const assigned = new Map<string, number>();
  branches.forEach((b) => assigned.set(b.id, columnOf.get(b.id)!));

  for (const edge of edges) {
    if (edge.relationship !== "ON_BRANCH") continue;
    const col = columnOf.get(edge.target);
    if (col !== undefined && !assigned.has(edge.source)) assigned.set(edge.source, col);
  }
  // One more pass: pull in each PR's direct neighbors into the same column as the PR.
  for (const edge of edges) {
    if (edge.relationship === "ON_BRANCH") continue;
    const sourceCol = assigned.get(edge.source);
    const targetCol = assigned.get(edge.target);
    if (sourceCol !== undefined && targetCol === undefined) assigned.set(edge.target, sourceCol);
    else if (targetCol !== undefined && sourceCol === undefined) assigned.set(edge.source, targetCol);
  }

  const rowCounts = new Array(branches.length + 1).fill(0);
  const flowNodes: Node[] = [];

  for (const branch of branches) {
    const col = columnOf.get(branch.id)!;
    flowNodes.push({
      id: branch.id,
      position: { x: col * COLUMN_WIDTH, y: 0 },
      data: { label: branchHeaderLabel(branch) },
      className: "!w-56 rounded-card border-2 border-accent bg-accent-subtle px-3 py-2 shadow-card",
      draggable: false,
    });
  }

  for (const node of nodes) {
    if (node.type === "BRANCH") continue;
    const col = assigned.get(node.id) ?? unassignedColumn;
    const row = rowCounts[col]++;
    flowNodes.push({
      id: node.id,
      position: { x: col * COLUMN_WIDTH, y: HEADER_HEIGHT + row * ROW_HEIGHT },
      data: { label: nodeLabel(node, edges) },
      className: "!w-56 card px-3 py-2",
    });
  }

  if (rowCounts[unassignedColumn] > 0) {
    flowNodes.push({
      id: "__unassigned_header__",
      position: { x: unassignedColumn * COLUMN_WIDTH, y: 0 },
      data: {
        label: (
          <div className="w-full text-center text-xs font-semibold uppercase tracking-wide text-muted">{UNASSIGNED_LABEL}</div>
        ),
      },
      className: "!w-56 rounded-card border border-border bg-surface px-3 py-2",
      draggable: false,
      selectable: false,
    });
  }

  const flowEdges: Edge[] = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.relationship,
    style: e.relationship === "BLOCKS" || e.relationship === "DEPENDS_ON" ? { stroke: "#B45309" } : undefined,
  }));

  return { nodes: flowNodes, edges: flowEdges };
}

export function GraphView({ projectId }: { projectId: string }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGraph(projectId)
      .then((data) => {
        const laid = layoutByBranch(data.nodes, data.edges);
        setNodes(laid.nodes);
        setEdges(laid.edges);
      })
      .catch((err) => setError(String(err)));
  }, [projectId]);

  if (error) return <div className="p-4 text-status-conflicted">{error}</div>;

  return (
    <div className="h-full w-full bg-surface">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#E4E9F0" />
        <Controls />
      </ReactFlow>
    </div>
  );
}
