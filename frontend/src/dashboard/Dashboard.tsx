import { useEffect, useState } from "react";
import { fetchDashboard, type DashboardResponse } from "../api/client";

const STAT_CARDS: { key: keyof DashboardResponse["counts"]; label: string; color: string }[] = [
  { key: "active", label: "Active", color: "bg-green-100 text-green-800" },
  { key: "blocked", label: "Blocked", color: "bg-amber-100 text-amber-800" },
  { key: "conflicted", label: "Conflicted", color: "bg-red-100 text-red-800" },
  { key: "unknown", label: "Unknown", color: "bg-gray-100 text-gray-800" },
];

export function Dashboard({ projectId }: { projectId: string }) {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard(projectId)
      .then(setData)
      .catch((err) => setError(String(err)));
  }, [projectId]);

  if (error) return <div className="p-4 text-red-600">{error}</div>;
  if (!data) return <div className="p-4 text-gray-500">Loading…</div>;

  return (
    <div className="space-y-6 overflow-auto p-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {STAT_CARDS.map(({ key, label, color }) => (
          <div key={key} className={`rounded p-4 text-center ${color}`}>
            <div className="text-2xl font-bold">{data.counts[key]}</div>
            <div className="text-sm">{label}</div>
          </div>
        ))}
      </div>

      <section>
        <h2 className="mb-2 font-semibold">Critical Dependencies</h2>
        {data.risks.length === 0 ? (
          <div className="text-sm text-gray-500">No dependency chains currently at risk.</div>
        ) : (
          <div className="space-y-2">
            {data.risks.map((risk) => (
              <div key={risk.source_node.id} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="rounded bg-amber-100 px-2 py-0.5">{risk.source_node.name}</span>
                {risk.chain.map((step) => (
                  <span key={step.edge.id} className="flex items-center gap-2">
                    <span className="text-gray-400">→</span>
                    <span className="rounded bg-gray-100 px-2 py-0.5">{step.node?.name ?? "unknown"}</span>
                  </span>
                ))}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 font-semibold">Detected Risks</h2>
        {data.risks.length === 0 && data.conflicts.length === 0 && data.crossed_deadlines.length === 0 ? (
          <div className="text-sm text-gray-500">Nothing to flag right now.</div>
        ) : (
          <ul className="space-y-1 text-sm">
            {data.conflicts.map((c) => (
              <li key={`conflict-${c.node.id}`}>⚠ {c.node.name} state conflict</li>
            ))}
            {data.risks.map((r) => (
              <li key={`risk-${r.source_node.id}`}>⚠ {r.source_node.name} status uncertain, downstream impact possible</li>
            ))}
            {data.crossed_deadlines.map((d) => (
              <li key={`deadline-${d.deadline.id}`}>⚠ Deadline {d.date} passed for {d.deadline.name}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
