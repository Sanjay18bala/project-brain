import { useState } from "react";
import { investigate } from "../api/client";

type Message = { role: "user" | "assistant"; text: string };

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
      const { answer } = await investigate(projectId, question);
      setMessages((prev) => [...prev, { role: "assistant", text: answer }]);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col p-4">
      <div className="flex-1 space-y-3 overflow-auto">
        {messages.length === 0 && (
          <div className="text-sm text-gray-400">
            Try: "What is blocking us?", "Why is deployment at risk?", "Show me conflicting information."
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span
              className={
                m.role === "user"
                  ? "inline-block max-w-[80%] rounded bg-blue-100 px-3 py-1"
                  : "inline-block max-w-[80%] rounded bg-gray-100 px-3 py-1"
              }
            >
              {m.text}
            </span>
          </div>
        ))}
        {loading && <div className="text-sm text-gray-400">Thinking…</div>}
        {error && <div className="text-sm text-red-600">{error}</div>}
      </div>
      <div className="mt-2 flex gap-2">
        <input
          className="flex-1 rounded border px-2 py-1"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Why is deployment at risk?"
        />
        <button className="rounded bg-blue-600 px-3 py-1 text-white disabled:opacity-50" onClick={ask} disabled={loading}>
          Ask
        </button>
      </div>
    </div>
  );
}
