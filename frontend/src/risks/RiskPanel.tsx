import { useEffect, useState } from "react";
import { fetchRisks, type RisksResponse } from "../api/client";

export function RiskPanel({ projectId }: { projectId: string }) {
  const [data, setData] = useState<RisksResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRisks(projectId)
      .then(setData)
      .catch((err) => setError(String(err)));
  }, [projectId]);

  if (error) return <div className="p-6 text-status-conflicted">{error}</div>;
  if (!data) return <div className="p-6 text-muted">Loading…</div>;
  if (data.risks.length === 0) return <div className="p-6 text-muted">No downstream risks detected.</div>;

  return (
    <div className="h-full space-y-4 overflow-auto bg-surface p-6">
      {data.risks.map((risk) => (
        <div key={risk.source_node.id} className="card border-l-4 border-l-status-blocked p-4">
          <div className="font-semibold text-status-blocked">
            {risk.source_node.name} is CONFLICTED — potential downstream impact
          </div>
          <div className="mt-2.5 flex flex-wrap items-center gap-2 text-sm">
            <span className="badge-conflicted">{risk.source_node.name}</span>
            {risk.chain.map((step, i) => (
              <span key={step.edge.id} className="flex items-center gap-2">
                <span className="text-muted">→ {step.edge.relationship} →</span>
                <span className={i === risk.chain.length - 1 ? "badge-blocked" : "badge-unknown"}>
                  {step.node?.name ?? "unknown"}
                </span>
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
