import type { GraphEdge, GraphNode } from "../api/client";

const BLOCKING_RELATIONSHIPS = new Set(["BLOCKS", "DEPENDS_ON"]);

export type StatusBucket = "active" | "blocked" | "conflicted" | "unknown";

/** Mirrors backend/app/agents/dashboard.py's summarize_node_counts exactly, so the same
 * node always gets the same status color everywhere in the UI. */
export function classifyNode(node: GraphNode, edges: GraphEdge[]): StatusBucket {
  if (node.status === "CONFLICTED") return "conflicted";
  if (node.status === "UNKNOWN") return "unknown";
  const isBlocked = edges.some((e) => BLOCKING_RELATIONSHIPS.has(e.relationship) && e.target === node.id);
  return isBlocked ? "blocked" : "active";
}

export const STATUS_BADGE_CLASS: Record<StatusBucket, string> = {
  active: "badge-active",
  blocked: "badge-blocked",
  conflicted: "badge-conflicted",
  unknown: "badge-unknown",
};
