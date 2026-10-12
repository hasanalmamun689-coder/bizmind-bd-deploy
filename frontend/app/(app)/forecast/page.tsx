"use client";
import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFetch } from "@/hooks/useFetch";
import { Async, Badge, Card, EmptyState, KpiCard, PageHeader, Select } from "@/components/ui";
import { dateShort, num } from "@/lib/format";
import type { Forecast, Product } from "@/types";

export default function ForecastPage() {
  const products = useFetch<Product[]>("/api/products", { page_size: 200 });
  const [pid, setPid] = useState("");
  const [horizon, setHorizon] = useState("14");
  useEffect(() => { if (!pid && products.data?.length) setPid(products.data[0].id); }, [products.data, pid]);
  const fc = useFetch<Forecast>(pid ? `/api/forecast/${pid}` : null, { horizon_days: horizon });
  const hist = useFetch<{ date: string; units: number }[]>(pid ? `/api/forecast/${pid}/history` : null, { days: 60 });
  const product = products.data?.find((p) => p.id === pid);

  return (
    <>
      <PageHeader title="Demand forecast" subtitle="Simple, transparent models. A forecast is an estimate, never a guarantee." />
      <Async state={products} empty={{ when: (d) => d.length === 0, message: "No products yet. Add products and record sales to forecast demand." }}>{() => (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            <Select aria-label="Product" className="w-64" value={pid} onChange={(e) => setPid(e.target.value)}>{products.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select>
            <Select aria-label="Forecast horizon" className="w-40" value={horizon} onChange={(e) => setHorizon(e.target.value)}><option value="7">7 days</option><option value="14">14 days</option><option value="30">30 days</option></Select>
          </div>
          <Async state={fc}>{(f) => f.insufficient_data ? (
            <Card><EmptyState message="Not enough sales history for this product (at least 7 days of sales are needed). The system will not guess — record more sales and check back." /></Card>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
                <KpiCard label={`Expected demand (${f.horizon_days}d)`} value={`${num(Math.round(f.predicted_demand))} units`} hint={`≈ ${(f.predicted_demand / f.horizon_days).toFixed(1)} per day`} />
                <KpiCard label="Current stock" value={num(f.current_stock_at_run)} />
                <KpiCard label="Est. stockout" value={f.estimated_stockout_date ? dateShort(f.estimated_stockout_date) : "None expected"} tone={f.risk_level === "critical" || f.risk_level === "high" ? "bad" : undefined} />
                <div className="rounded-xl border bg-slate-900/70 p-4 shadow-sm"><p className="text-xs font-medium uppercase tracking-wide text-slate-400">Risk level</p><div className="mt-2"><Badge value={f.risk_level} /></div></div>
                <KpiCard label="Model" value="Exp. smoothing" hint="α = 0.3, last 90 days of sales" />
              </div>
              <Card title="Historical daily sales and expected demand">
                <Async state={hist}>{(h) => {
                  const perDay = f.predicted_demand / f.horizon_days;
                  const future = Array.from({ length: f.horizon_days }, (_, i) => { const d = new Date(); d.setDate(d.getDate() + i + 1); return { date: d.toISOString().slice(0, 10), expected: +perDay.toFixed(2) }; });
                  const data = [...h.map((x) => ({ date: x.date, units: x.units })), ...future];
                  return <div className="h-72"><ResponsiveContainer><LineChart data={data}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} fontSize={11} /><YAxis fontSize={11} width={35} /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} /><Legend />
                    <Line type="monotone" dataKey="units" name="Units sold" stroke="#6366f1" dot={false} strokeWidth={2} /><Line type="monotone" dataKey="expected" name="Expected per day" stroke="#f97316" strokeDasharray="5 4" dot={false} strokeWidth={2} />
                    <ReferenceLine x={new Date().toISOString().slice(0, 10)} stroke="#64748b" label={{ value: "Today", fontSize: 11 }} /></LineChart></ResponsiveContainer></div>; }}</Async>
                <p className="mt-2 text-xs text-slate-400">Method: exponentially-smoothed average of daily units sold, projected flat over the horizon and compared with current stock{product ? ` (${product.current_stock} ${product.unit})` : ""}. It does not model seasonality or promotions.</p>
              </Card>
            </>
          )}</Async>
        </div>)}</Async>
    </>
  );
}
