import { useState } from "react";
import { investigate, type Source } from "../api/client";

type Message = { role: "user" | "assistant"; text: string; sources?: Source[] };

export function AgentChat({ projectId }: { projectId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask() {
    const question = input.trim();
    if (!question || loading) return;
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const { answer, sources } = await investigate(projectId, question);
      setMessages((prev) => [...prev, { role: "assistant", text: answer, sources }]);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col bg-surface p-6">
      <div className="flex-1 space-y-3 overflow-auto">
        {messages.length === 0 && (
          <div className="text-sm text-muted">
            Try: "What is blocking us?", "Why is deployment at risk?", "Show me conflicting information."
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span
              className={
                m.role === "user"
                  ? "inline-block max-w-[80%] rounded-card bg-accent-subtle px-3 py-1.5 text-sm text-ink"
                  : "inline-block max-w-[80%] rounded-card border border-border bg-panel px-3 py-1.5 text-sm text-ink shadow-card"
              }
            >
              {m.text}
            </span>
            {m.sources && m.sources.length > 0 && (
              <div className="mt-1 text-left text-xs text-muted">
                Based on:{" "}
                {m.sources.map((s, si) => (
                  <span key={si}>
                    {si > 0 && ", "}
                    {s.url ? (
                      <a href={s.url} target="_blank" rel="noreferrer" className="text-accent underline">
                        {s.node_name}
                      </a>
                    ) : (
                      <span>{s.node_name}</span>
                    )}{" "}
                    ({s.source_type})
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-sm text-muted">Thinking…</div>}
        {error && <div className="text-sm text-status-conflicted">{error}</div>}
      </div>
      <div className="mt-3 flex gap-2">
        <input
          className="flex-1 rounded-lg border border-border bg-panel px-3 py-1.5 text-sm text-ink"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Why is deployment at risk?"
        />
        <button className="btn-primary" onClick={ask} disabled={loading}>
          Ask
        </button>
      </div>
    </div>
  );
}
