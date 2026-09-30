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

  if (error) return <div className="p-6 text-status-conflicted">{error}</div>;
  if (!data) return <div className="p-6 text-muted">Loading…</div>;
  if (data.conflicts.length === 0) return <div className="p-6 text-muted">No conflicts detected.</div>;

  return (
    <div className="h-full space-y-4 overflow-auto bg-surface p-6">
      {data.conflicts.map((conflict) => (
        <div key={conflict.node.id} className="card border-l-4 border-l-status-conflicted p-4">
          <div className="font-semibold text-status-conflicted">
            {conflict.node.name} <span className="text-sm font-normal text-muted">({conflict.node.type})</span>
          </div>
          <ul className="mt-2.5 space-y-1.5 text-sm">
            {conflict.claims.map((claim, i) => (
              <li key={`${claim.source_type}-${claim.source_ref}-${i}`} className={i === 0 ? "font-medium text-ink" : "text-muted"}>
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
