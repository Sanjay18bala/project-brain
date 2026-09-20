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

  if (error) return <div className="p-4 text-red-600">{error}</div>;
  if (!data) return <div className="p-4 text-gray-500">Loading…</div>;
  if (data.risks.length === 0) return <div className="p-4 text-gray-500">No downstream risks detected.</div>;

  return (
    <div className="space-y-4 overflow-auto p-4">
      {data.risks.map((risk) => (
        <div key={risk.source_node.id} className="rounded border border-amber-400 p-3">
          <div className="font-semibold text-amber-700">
            ⚠ {risk.source_node.name} is CONFLICTED — potential downstream impact
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-gray-700">
            <span className="rounded bg-amber-100 px-2 py-0.5">{risk.source_node.name}</span>
            {risk.chain.map((step, i) => (
              <span key={step.edge.id} className="flex items-center gap-2">
                <span className="text-gray-400">→ {step.edge.relationship} →</span>
                <span className={i === risk.chain.length - 1 ? "rounded bg-red-100 px-2 py-0.5" : "rounded bg-gray-100 px-2 py-0.5"}>
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
