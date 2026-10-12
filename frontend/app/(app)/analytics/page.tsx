"use client";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFetch } from "@/hooks/useFetch";
import { Async, Badge, Card, KpiCard, PageHeader, Select, Table, cx } from "@/components/ui";
import { num, taka, titleCase } from "@/lib/format";
import type { InventoryAnalytics, ProfitBreakdown, SupplierAnalytics, TopProduct } from "@/types";

const TABS = ["Sales", "Inventory", "Profit", "Suppliers"] as const;
const fmtK = (v: number) => (Math.abs(v) >= 1000 ? `${Math.round(v / 1000)}k` : String(v));

function SalesTab({ days }: { days: string }) {
  const s = useFetch<{ trend: { date: string; revenue: number; orders: number }[]; top_products: TopProduct[] }>("/api/analytics/sales", { days });
  const cats = useFetch<{ category: string; revenue: number; gross_profit: number; units: number }[]>("/api/analytics/categories", { days });
  return (
    <Async state={s} empty={{ when: (d) => d.trend.length === 0, message: "No sales in this period." }}>{(d) => {
      const rev = d.trend.reduce((a, r) => a + r.revenue, 0), orders = d.trend.reduce((a, r) => a + r.orders, 0);
      return <div className="space-y-5">
        <div className="grid grid-cols-3 gap-3"><KpiCard label="Revenue" value={taka(rev)} /><KpiCard label="Orders" value={num(orders)} /><KpiCard label="Avg order value" value={taka(orders ? rev / orders : 0)} /></div>
        <Card title="Revenue trend"><div className="h-64"><ResponsiveContainer><LineChart data={d.trend}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} fontSize={11} /><YAxis tickFormatter={fmtK} fontSize={11} width={40} /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} formatter={(v: number) => taka(v)} /><Line type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></Card>
        <div className="grid gap-5 lg:grid-cols-2">
          <Card title="Top products (all time)"><Table rows={d.top_products} rowKey={(r) => r.product_id} cols={[{ header: "Product", cell: (r) => r.name }, { header: "Units", cell: (r) => num(r.units_sold), className: "text-right" }, { header: "Revenue", cell: (r) => taka(r.revenue), className: "text-right" }]} /></Card>
          <Card title="Category performance"><Async state={cats}>{(c) => <Table rows={c} rowKey={(r) => r.category} cols={[{ header: "Category", cell: (r) => r.category }, { header: "Units", cell: (r) => num(r.units), className: "text-right" }, { header: "Revenue", cell: (r) => taka(r.revenue), className: "text-right" }, { header: "Gross profit", cell: (r) => taka(r.gross_profit), className: "text-right" }]} />}</Async></Card>
        </div></div>; }}</Async>
  );
}

function InventoryTab() {
  const s = useFetch<InventoryAnalytics>("/api/analytics/inventory");
  return <Async state={s}>{(d) => <div className="space-y-5">
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5"><KpiCard label="Inventory value" value={taka(d.total_inventory_value)} hint="At purchase price" />
      {["healthy", "low_stock", "critical", "overstock"].map((k) => <KpiCard key={k} label={titleCase(k)} value={String(d.status_breakdown[k] ?? 0)} tone={k === "healthy" ? "good" : k === "overstock" ? undefined : "warn"} />)}</div>
    <Card title="Dead stock (in stock, no sales in 60 days)">{d.dead_stock.length === 0 ? <p className="text-sm text-slate-400">No dead stock detected.</p> :
      <Table rows={d.dead_stock} rowKey={(r) => r.product_id} cols={[{ header: "Product", cell: (r) => r.name }, { header: "Units on hand", cell: (r) => num(r.current_stock), className: "text-right" }]} />}</Card></div>}</Async>;
}

function ProfitTab({ days }: { days: string }) {
  const s = useFetch<ProfitBreakdown>("/api/analytics/profit", { days });
  const m = useFetch<{ month: string; revenue: number; cost_of_goods_sold: number; expenses: number; estimated_profit: number }[]>("/api/analytics/monthly");
  return <Async state={s}>{(p) => <div className="space-y-5">
    <Card title={`Profit calculation (last ${p.period_days} days)`}>
      <dl className="max-w-md space-y-2 text-sm">
        <div className="flex justify-between"><dt>Revenue</dt><dd className="font-medium">{taka(p.revenue)}</dd></div>
        <div className="flex justify-between text-slate-300"><dt>− Cost of goods sold</dt><dd>{taka(p.cost_of_goods_sold)}</dd></div>
        <div className="flex justify-between border-t pt-2"><dt>= Gross profit <span className="text-xs text-slate-400">({p.gross_margin_percent}% margin)</span></dt><dd className="font-medium">{taka(p.gross_profit)}</dd></div>
        <div className="flex justify-between text-slate-300"><dt>− Operating expenses</dt><dd>{taka(p.operating_expenses)}</dd></div>
        <div className="flex justify-between border-t pt-2 text-base"><dt className="font-semibold">= Estimated profit</dt><dd className={cx("font-semibold", p.estimated_profit < 0 ? "text-rose-400" : "text-emerald-400")}>{taka(p.estimated_profit)}</dd></div>
      </dl>
      <p className="mt-3 text-xs text-slate-400">An estimate from recorded sales and expenses — not audited accounting profit.</p></Card>
    <Card title="Monthly profit breakdown"><Async state={m}>{(rows) => <div className="h-64"><ResponsiveContainer><BarChart data={rows}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" fontSize={11} /><YAxis tickFormatter={fmtK} fontSize={11} width={40} /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} formatter={(v: number) => taka(v)} /><Legend />
      <Bar dataKey="cost_of_goods_sold" name="COGS" stackId="a" fill="#64748b" /><Bar dataKey="expenses" name="Expenses" stackId="a" fill="#f59e0b" /><Bar dataKey="estimated_profit" name="Est. profit" fill="#10b981" /></BarChart></ResponsiveContainer></div>}</Async></Card></div>}</Async>;
}

function SuppliersTab() {
  const s = useFetch<SupplierAnalytics[]>("/api/analytics/suppliers");
  return <Async state={s} empty={{ when: (d) => d.length === 0, message: "No suppliers yet." }}>{(rows) => <Table rows={rows} rowKey={(r) => r.supplier_id} cols={[
    { header: "Supplier", cell: (r) => <b>{r.name}</b> }, { header: "Orders", cell: (r) => r.order_count, className: "text-right" }, { header: "Delivery", cell: (r) => `${r.delivery_time_days}d`, className: "text-right" },
    { header: "Reliability", cell: (r) => <Badge value={r.reliability_score >= 80 ? "healthy" : r.reliability_score >= 60 ? "low_stock" : "critical"} label={String(r.reliability_score)} /> },
    { header: "Quality", cell: (r) => r.quality_score, className: "text-right" }, { header: "Fulfillment", cell: (r) => `${r.fulfillment_rate}%`, className: "text-right" }]} />}</Async>;
}

export default function AnalyticsPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Sales");
  const [days, setDays] = useState("30");
  return (
    <>
      <PageHeader title="Analytics" subtitle="Sales, inventory, profitability and supplier performance from your real records."
        action={tab === "Sales" || tab === "Profit" ? <Select aria-label="Period" className="w-40" value={days} onChange={(e) => setDays(e.target.value)}><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="180">Last 180 days</option></Select> : undefined} />
      <div role="tablist" className="mb-5 flex gap-1 border-b">{TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={cx("-mb-px border-b-2 px-4 py-2 text-sm font-medium", tab === t ? "border-indigo-500 text-indigo-300" : "border-transparent text-slate-400 hover:text-white")}>{t}</button>)}</div>
      {tab === "Sales" && <SalesTab days={days} />}{tab === "Inventory" && <InventoryTab />}{tab === "Profit" && <ProfitTab days={days} />}{tab === "Suppliers" && <SuppliersTab />}
    </>
  );
}
