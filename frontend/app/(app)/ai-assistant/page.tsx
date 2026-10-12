"use client";
import { useEffect, useRef, useState, FormEvent } from "react";
import { Bot, Send, User } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge, Button, Input } from "@/components/ui";
import { titleCase } from "@/lib/format";
import type { ChatResponse } from "@/types";

const SUGGESTIONS = ["What should I purchase this week?", "Why did my profit decrease this month?", "What are my biggest business risks?", "Which products are selling fastest?", "Which supplier gives me the best deal?", "Why are my expenses increasing?"];

type Msg = { role: "user"; text: string } | { role: "assistant"; res: ChatResponse } | { role: "error"; text: string };

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="mt-3"><p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{title}</p><div className="mt-1 text-xs leading-relaxed text-slate-300">{children}</div></div>;
}

/** Renders one tool result compactly and honestly — raw figures from the database, nothing rewritten. */
function ToolResult({ name, result, error }: { name: string; result?: any; error?: string }) {
  if (error) return <p className="text-xs text-rose-400">{name}: {error}</p>;
  const pretty = (v: any) => (typeof v === "number" ? v.toLocaleString("en-IN") : String(v));
  const scalar = result && typeof result === "object" ? Object.entries(result).filter(([, v]) => typeof v !== "object" || v === null) : [];
  const lists = result && typeof result === "object" ? Object.entries(result).filter(([, v]) => Array.isArray(v) && (v as any[]).length && typeof (v as any[])[0] === "object") : [];
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5">
      <p className="mb-1 text-xs font-semibold text-slate-300">{titleCase(name.replace(/^get_/, ""))}</p>
      {scalar.length > 0 && <dl className="grid grid-cols-2 gap-x-3 text-xs">{scalar.map(([k, v]) => <div key={k} className="contents"><dt className="text-slate-400">{titleCase(k)}</dt><dd className="text-right font-medium">{pretty(v)}</dd></div>)}</dl>}
      {lists.map(([k, rows]) => { const arr = (rows as any[]).slice(0, 8); const cols = Object.keys(arr[0]).filter((c) => !c.endsWith("_id") && typeof arr[0][c] !== "object").slice(0, 5);
        return <div key={k} className="mt-2 overflow-x-auto"><p className="text-xs text-slate-400">{titleCase(k)}{(rows as any[]).length > 8 ? ` (first 8 of ${(rows as any[]).length})` : ""}</p>
          <table className="mt-1 w-full text-xs"><thead className="text-left text-slate-400"><tr>{cols.map((c) => <th key={c} className="pr-3 font-medium">{titleCase(c)}</th>)}</tr></thead><tbody>{arr.map((r, i) => <tr key={i} className="border-t">{cols.map((c) => <td key={c} className="pr-3 py-0.5">{pretty(r[c])}</td>)}</tr>)}</tbody></table></div>; })}
    </div>
  );
}

export default function AiAssistantPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [convo, setConvo] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  async function ask(q: string) {
    if (!q.trim() || busy) return;
    setMsgs((m) => [...m, { role: "user", text: q }]); setText(""); setBusy(true);
    try { const res = await api<ChatResponse>("/api/ai/chat", { method: "POST", body: { message: q, conversation_id: convo } }); setConvo(res.conversation_id); setMsgs((m) => [...m, { role: "assistant", res }]); }
    catch (err) { setMsgs((m) => [...m, { role: "error", text: err instanceof ApiError ? err.message : "The assistant couldn't answer right now. Please try again." }]); }
    finally { setBusy(false); }
  }
  const onSubmit = (e: FormEvent) => { e.preventDefault(); ask(text); };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-slate-800 bg-slate-900/80 px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-4xl items-center gap-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 text-white shadow-lg shadow-indigo-950/50"><Bot className="h-5 w-5" aria-hidden /></span><div><div className="flex items-center gap-2"><h1 className="text-base font-bold text-white">BizMind BD Copilot</h1><span className="rounded border border-cyan-500/30 bg-cyan-500/20 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-cyan-300">Grounded in your data</span></div><p className="text-xs text-slate-400">Answers use only your real business data through controlled tools. It cannot run SQL or place orders.</p></div></div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-4xl space-y-4">

          {msgs.length === 0 && <div className="py-6 text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-500 to-indigo-600 text-white shadow-lg shadow-indigo-950/50"><Bot className="h-7 w-7" aria-hidden /></span><h2 className="mt-4 text-lg font-bold text-white">How can I help your business today?</h2><p className="mt-1 text-sm text-slate-400">Ask about sales, stock, suppliers, profit or risks.</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">{SUGGESTIONS.map((s) => <button key={s} onClick={() => ask(s)} className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 transition hover:border-indigo-500 hover:text-white">{s}</button>)}</div></div>}
          {msgs.map((m, i) => m.role === "user" ? (
            <div key={i} className="flex justify-end gap-2"><div className="max-w-[85%] rounded-2xl rounded-tr-none bg-indigo-600 px-4 py-2.5 text-xs font-medium text-white shadow-md">{m.text}</div><User className="mt-1 h-5 w-5 shrink-0 text-slate-500" aria-hidden /></div>
          ) : m.role === "error" ? (
            <p key={i} role="alert" className="rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-300">{m.text}</p>
          ) : (
            <div key={i} className="flex gap-2"><span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-indigo-500/40 bg-indigo-600/30 text-cyan-400"><Bot className="h-4 w-4" aria-hidden /></span>
              <div className="max-w-full flex-1 rounded-2xl rounded-tl-none border border-slate-800 bg-slate-950/80 p-4 shadow-md">
                <div className="flex items-center gap-2"><Badge value={m.res.used_live_model ? "approved" : "draft"} label={m.res.used_live_model ? "AI model + your data" : "Data-only mode (no AI model configured)"} /></div>
                <Section title="Answer"><p className="whitespace-pre-wrap text-slate-200">{m.res.answer}</p></Section>
                <Section title="Evidence"><div className="space-y-2">{m.res.evidence.tool_results.map((t, j) => <ToolResult key={j} name={t.tool} result={t.result} error={t.error} />)}</div></Section>
                <Section title="Reasoning"><p>{m.res.reasoning}</p></Section>
                {m.res.suggested_action && <Section title="Suggested action"><p className="font-medium text-cyan-300">{m.res.suggested_action}</p></Section>}
              </div></div>
          ))}
          {busy && <p role="status" className="flex items-center gap-2 text-xs text-slate-400"><span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400" />Analyzing your live business data…</p>}
          <div ref={end} />
        </div>
      </div>
      <div className="border-t border-slate-800 bg-slate-900/80 px-4 py-3 sm:px-6">
        <form onSubmit={onSubmit} className="mx-auto flex max-w-4xl gap-2">
          <Input aria-label="Ask a question" placeholder="e.g. What should I purchase this week?" value={text} onChange={(e) => setText(e.target.value)} disabled={busy} />
          <Button type="submit" disabled={busy || !text.trim()}><Send className="h-4 w-4" /><span className="sr-only sm:not-sr-only">Ask</span></Button>
        </form>
      </div>
    </div>

  );
}
