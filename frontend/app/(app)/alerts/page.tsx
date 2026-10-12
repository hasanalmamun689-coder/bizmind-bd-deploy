"use client";
import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Card, PageHeader, Select, useToast } from "@/components/ui";
import { dateTime, titleCase } from "@/lib/format";
import type { Alert, Risk } from "@/types";

export default function AlertsPage() {
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const alerts = useFetch<Alert[]>("/api/alerts", { severity, status });
  const risks = useFetch<Risk[]>("/api/alerts/risks");
  const toast = useToast();
  async function setState(a: Alert, s: string) {
    try { await api(`/api/alerts/${a.id}/status`, { method: "PUT", params: { new_status: s } }); alerts.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not update the alert."); }
  }
  return (
    <>
      <PageHeader title="Alerts & risks" subtitle="Every risk shows its evidence. When there isn't enough data, the system says so." />
      <Card title="Detected business risks (live analysis)" className="mb-5">
        <Async state={risks}>{(r) => <ul className="grid gap-3 md:grid-cols-2">{r.map((x) => (
          <li key={x.risk} className="rounded-lg border p-3">
            <div className="flex items-center gap-2"><Badge value={x.severity} /><b className="text-sm">{x.risk}</b></div>
            <p className="mt-1 text-sm text-slate-300">{x.explanation}</p>
            {Object.keys(x.evidence).length > 0 && <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 rounded bg-slate-950/60 p-2 text-xs">{Object.entries(x.evidence).filter(([k]) => !k.endsWith("_id")).map(([k, v]) => <div key={k} className="contents"><dt className="text-slate-400">{titleCase(k)}</dt><dd className="text-right font-medium">{typeof v === "number" ? v.toLocaleString("en-IN") : String(v)}</dd></div>)}</dl>}
            <p className="mt-2 text-xs text-slate-400"><b>Investigate:</b> {x.recommended_investigation}</p>
          </li>))}</ul>}</Async>
      </Card>
      <div className="mb-3 flex flex-wrap gap-2">
        <Select aria-label="Severity" className="w-40" value={severity} onChange={(e) => setSeverity(e.target.value)}><option value="">All severities</option><option value="critical">Critical</option><option value="warning">Warning</option><option value="info">Info</option></Select>
        <Select aria-label="Status" className="w-40" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option>{["unread", "read", "resolved", "dismissed"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</Select>
      </div>
      <Async state={alerts} empty={{ when: (d) => d.length === 0, message: "No alerts match. Stock and sales alerts appear automatically as your data changes." }}>{(rows) => (
        <ul className="space-y-3">{rows.map((a) => (
          <li key={a.id} className={`rounded-xl border bg-slate-900/70 p-4 shadow-sm ${a.status === "unread" ? "border-l-4 border-l-indigo-500" : ""}`}>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div><div className="flex flex-wrap items-center gap-2"><Badge value={a.severity} /><Badge value={a.status} /><span className="text-xs text-slate-400">{titleCase(a.type)} · {dateTime(a.created_at)}</span></div>
                <p className="mt-1.5 font-medium">{a.title}</p><p className="text-sm text-slate-300">{a.description}</p>{a.suggested_action && <p className="mt-1 text-xs text-slate-400"><b>Suggested:</b> {a.suggested_action}</p>}</div>
              <div className="flex gap-1">{a.status === "unread" && <Button size="sm" variant="secondary" onClick={() => setState(a, "read")}>Mark read</Button>}
                {!["resolved", "dismissed"].includes(a.status) && <><Button size="sm" onClick={() => setState(a, "resolved")}>Resolve</Button><Button size="sm" variant="ghost" onClick={() => setState(a, "dismissed")}>Dismiss</Button></>}</div>
            </div></li>))}</ul>)}</Async>
    </>
  );
}
