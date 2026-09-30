import { useEffect, useState } from "react";
import { fetchDashboard, type DashboardResponse } from "../api/client";

const STAT_CARDS: { key: keyof DashboardResponse["counts"]; label: string; border: string; text: string }[] = [
  { key: "active", label: "Active", border: "border-l-status-active", text: "text-status-active" },
  { key: "blocked", label: "Blocked", border: "border-l-status-blocked", text: "text-status-blocked" },
  { key: "conflicted", label: "Conflicted", border: "border-l-status-conflicted", text: "text-status-conflicted" },
  { key: "unknown", label: "Unknown", border: "border-l-status-unknown", text: "text-status-unknown" },
];

export function Dashboard({ projectId }: { projectId: string }) {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard(projectId)
      .then(setData)
      .catch((err) => setError(String(err)));
  }, [projectId]);

  if (error) return <div className="p-6 text-status-conflicted">{error}</div>;
  if (!data) return <div className="p-6 text-muted">Loading…</div>;

  const nothingToFlag = data.risks.length === 0 && data.conflicts.length === 0 && data.crossed_deadlines.length === 0;

  return (
    <div className="h-full space-y-6 overflow-auto bg-surface p-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {STAT_CARDS.map(({ key, label, border, text }) => (
          <div key={key} className={`card border-l-4 ${border} px-4 py-3`}>
            <div className={`text-3xl font-semibold tabular-nums ${text}`}>{data.counts[key]}</div>
            <div className="mt-0.5 text-sm text-muted">{label}</div>
          </div>
        ))}
      </div>

      <section className="card p-5">
        <h2 className="text-base font-semibold tracking-tight text-ink">Critical Dependencies</h2>
        {data.risks.length === 0 ? (
          <div className="mt-3 text-sm text-muted">No dependency chains currently at risk.</div>
        ) : (
          <div className="mt-3 space-y-2.5">
            {data.risks.map((risk) => (
              <div key={risk.source_node.id} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="badge-blocked">{risk.source_node.name}</span>
                {risk.chain.map((step) => (
                  <span key={step.edge.id} className="flex items-center gap-2">
                    <span className="text-muted">→</span>
                    <span className="badge-unknown">{step.node?.name ?? "unknown"}</span>
                  </span>
                ))}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card p-5">
        <h2 className="text-base font-semibold tracking-tight text-ink">Detected Risks</h2>
        {nothingToFlag ? (
          <div className="mt-3 text-sm text-muted">Nothing to flag right now.</div>
        ) : (
          <ul className="mt-3 space-y-2 text-sm text-ink">
            {data.conflicts.map((c) => (
              <li key={`conflict-${c.node.id}`} className="flex items-center gap-2">
                <span className="badge-conflicted">Conflict</span>
                {c.node.name} has a state conflict
              </li>
            ))}
            {data.risks.map((r) => (
              <li key={`risk-${r.source_node.id}`} className="flex items-center gap-2">
                <span className="badge-blocked">Risk</span>
                {r.source_node.name} status uncertain, downstream impact possible
              </li>
            ))}
            {data.crossed_deadlines.map((d) => (
              <li key={`deadline-${d.deadline.id}`} className="flex items-center gap-2">
                <span className="badge-conflicted">Deadline</span>
                {d.date} passed for {d.deadline.name}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
