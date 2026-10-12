"use client";
import { useState } from "react";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { useFetch } from "@/hooks/useFetch";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Card, PageHeader, useToast } from "@/components/ui";
import { dateShort, taka } from "@/lib/format";
import type { Recommendation } from "@/types";

function Evidence({ ev }: { ev: Recommendation["evidence"] }) {
  const s = ev.recommended_supplier;
  return (
    <div className="grid gap-3 text-sm md:grid-cols-2">
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 rounded-lg bg-slate-950/60 p-3">
        <dt className="text-slate-400">Current stock</dt><dd className="text-right font-medium">{ev.current_stock}</dd>
        <dt className="text-slate-400">Avg daily demand</dt><dd className="text-right font-medium">{ev.avg_daily_demand}</dd>
        <dt className="text-slate-400">Est. days of stock</dt><dd className="text-right font-medium">{ev.estimated_days_of_stock ?? "—"}</dd>
        <dt className="text-slate-400">Stockout risk</dt><dd className="text-right"><Badge value={ev.risk_level} /></dd>
        <dt className="text-slate-400">Forecast model</dt><dd className="text-right font-medium">{String(ev.forecast_model).replace("_", " ")}</dd>
      </dl>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 rounded-lg bg-indigo-500/10 p-3">
        <dt className="text-slate-400">Suggested quantity</dt><dd className="text-right font-semibold">{ev.suggested_quantity}</dd>
        <dt className="text-slate-400">Recommended supplier</dt><dd className="text-right font-semibold">{s?.supplier}</dd>
        <dt className="text-slate-400">Unit price</dt><dd className="text-right font-medium">{taka(s?.price)}</dd>
        <dt className="text-slate-400">Estimated cost</dt><dd className="text-right font-semibold">{taka(ev.estimated_cost)}</dd>
        <dt className="text-slate-400">Expected delivery</dt><dd className="text-right font-medium">{s?.delivery_days} days</dd>
        <dt className="text-slate-400">Supplier reliability</dt><dd className="text-right font-medium">{s?.reliability}/100</dd>
      </dl>
      {Array.isArray(ev.supplier_options) && ev.supplier_options.length > 1 && (
        <div className="md:col-span-2"><p className="mb-1 text-xs font-medium text-slate-400">Supplier options considered</p>
          <table className="w-full text-xs"><thead className="text-left text-slate-400"><tr><th>Supplier</th><th className="text-right">Price</th><th className="text-right">MOQ</th><th className="text-right">Delivery</th><th className="text-right">Reliability</th></tr></thead>
            <tbody>{ev.supplier_options.map((o: any) => <tr key={o.supplier_id} className={o.supplier_id === s?.supplier_id ? "font-semibold" : "text-slate-300"}><td>{o.supplier}</td><td className="text-right">{taka(o.price)}</td><td className="text-right">{o.moq}</td><td className="text-right">{o.delivery_days}d</td><td className="text-right">{o.reliability}</td></tr>)}</tbody></table></div>)}
    </div>
  );
}

export default function RecommendationsPage() {
  const list = useFetch<Recommendation[]>("/api/ai/recommendations");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const toast = useToast();

  async function generate() {
    setGenerating(true);
    try { const r = await api<Recommendation[]>("/api/ai/recommendations/generate", { method: "POST" }); toast("success", r.length ? `${r.length} new recommendation(s) generated.` : "Nothing needs reordering right now (or there isn't enough sales history yet)."); list.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not generate recommendations."); }
    finally { setGenerating(false); }
  }
  async function decide(r: Recommendation, action: "approve" | "reject") {
    setBusyId(r.id);
    try { await api(`/api/ai/recommendations/${r.id}/${action}`, { method: "POST" });
      toast("success", action === "approve" ? "Approved. A purchase DRAFT was created — nothing has been ordered." : "Recommendation rejected."); list.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not record your decision."); }
    finally { setBusyId(null); }
  }

  return (
    <>
      <PageHeader title="AI recommendations" subtitle="Data → Forecast → Risk → Recommendation → Your approval → Purchase draft. AI never places orders."
        action={<Button onClick={generate} busy={generating}><Sparkles className="h-4 w-4" />Analyze &amp; recommend</Button>} />
      <Async state={list} empty={{ when: (d) => d.length === 0, message: "No recommendations yet. Click “Analyze & recommend” to check stock, demand forecasts and suppliers.", action: <Button onClick={generate} busy={generating}>Analyze &amp; recommend</Button> }}>
        {(rows) => <div className="space-y-4">{rows.map((r) => (
          <Card key={r.id} title={r.title} action={<Badge value={r.status} />}>
            <Evidence ev={r.evidence} />
            <div className="mt-3 rounded-lg border border-slate-800 p-3 text-sm"><p className="mb-0.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Reasoning</p><p className="text-slate-300">{r.reasoning}</p></div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-slate-400">Generated {dateShort(r.created_at)}</p>
              {r.status === "pending" ? <div className="flex gap-2"><Button variant="secondary" onClick={() => decide(r, "reject")} busy={busyId === r.id}>Reject</Button><Button onClick={() => decide(r, "approve")} busy={busyId === r.id}>Approve → create purchase draft</Button></div>
                : r.related_purchase_order_id ? <Link href="/procurement" className="text-sm text-indigo-300 hover:underline">View purchase draft in Procurement →</Link> : null}
            </div>
          </Card>))}</div>}
      </Async>
    </>
  );
}
