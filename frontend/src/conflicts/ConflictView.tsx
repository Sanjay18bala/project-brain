import { useEffect, useState } from "react";
import { fetchConflicts, type ConflictsResponse } from "../api/client";

export function ConflictView({ projectId }: { projectId: string }) {
  const [data, setData] = useState<ConflictsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConflicts(projectId)
      .then(setData)
      .catch((err) => setError(String(err)));
  }, [projectId]);

  if (error) return <div className="p-4 text-red-600">{error}</div>;
  if (!data) return <div className="p-4 text-gray-500">Loading…</div>;
  if (data.conflicts.length === 0) return <div className="p-4 text-gray-500">No conflicts detected.</div>;

  return (
    <div className="space-y-4 overflow-auto p-4">
      {data.conflicts.map((conflict) => (
        <div key={conflict.node.id} className="rounded border border-red-300 p-3">
          <div className="font-semibold text-red-700">
            ⚠ {conflict.node.name} <span className="text-sm text-gray-500">({conflict.node.type})</span>
          </div>
          <ul className="mt-2 space-y-1 text-sm">
            {conflict.claims.map((claim, i) => (
              <li key={`${claim.source_type}-${claim.source_ref}-${i}`} className={i === 0 ? "font-semibold" : "text-gray-600"}>
                {claim.source_type}: {claim.claimed_state} — score {claim.score.toFixed(2)} (
                {new Date(claim.occurred_at).toLocaleString()})
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
