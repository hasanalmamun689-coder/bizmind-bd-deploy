"use client";
import Link from "next/link";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFetch } from "@/hooks/useFetch";
import { Async, Badge, Card, KpiCard, PageHeader } from "@/components/ui";
import { dateShort, num, taka, titleCase } from "@/lib/format";
import type { Alert, Dashboard, HealthScore, Risk } from "@/types";

const fmtK = (v: number) => (Math.abs(v) >= 1000 ? `${Math.round(v / 1000)}k` : String(v));

export default function DashboardPage() {
  const dash = useFetch<Dashboard>("/api/analytics/dashboard");
  const monthly = useFetch<{ month: string; revenue: number; expenses: number; estimated_profit: number }[]>("/api/analytics/monthly");
  const cats = useFetch<{ category: string; revenue: number; gross_profit: number }[]>("/api/analytics/categories");
  const move = useFetch<{ date: string; stock_in: number; stock_out: number }[]>("/api/analytics/inventory-movement");
  const risks = useFetch<Risk[]>("/api/alerts/risks");
  const alerts = useFetch<Alert[]>("/api/alerts", { status: "unread" });
  const health = useFetch<HealthScore>("/api/analytics/health-score");

  return (
    <>
      <PageHeader title="Dashboard" subtitle="What happened, what may happen next, and what deserves your attention." />
      <Async state={dash} empty={{ when: (d) => d.kpis.total_sales === 0, message: "No sales recorded yet. Add products and record your first sale to see your business come to life." }}>
        {(d) => {
          const k = d.kpis;
          return (
            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <KpiCard label="Total sales" value={num(k.total_sales)} hint="Completed transactions" />
                <KpiCard label="Revenue" value={taka(k.revenue)} />
                <KpiCard label="Estimated profit" value={taka(k.estimated_profit)} tone={k.estimated_profit < 0 ? "bad" : "good"} hint="Revenue − COGS − expenses (estimate)" />
                <KpiCard label="Expenses" value={taka(k.total_expenses)} />
                <KpiCard label="Inventory value" value={taka(k.inventory_value)} hint="At purchase price" />
                <KpiCard label="Low-stock items" value={num(k.low_stock_items)} tone={k.low_stock_items ? "warn" : undefined} />
                <KpiCard label="Pending purchases" value={num(k.pending_purchases)} hint="Draft or awaiting approval" />
                <KpiCard label="Active customers" value={num(k.active_customers)} hint="Bought in last 90 days" />
              </div>

              <div className="grid gap-5 lg:grid-cols-2">
                <Card title="Sales trend (30 days)">
                  <div className="h-64"><ResponsiveContainer><AreaChart data={d.sales_trend}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} fontSize={11} /><YAxis tickFormatter={fmtK} fontSize={11} width={40} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} formatter={(v: number) => taka(v)} /><Area type="monotone" dataKey="revenue" name="Revenue" stroke="#6366f1" fill="#312e81" /></AreaChart></ResponsiveContainer></div>
                </Card>
                <Card title="Revenue vs expenses (monthly)">
                  <Async state={monthly}>{(m) => <div className="h-64"><ResponsiveContainer><BarChart data={m}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" fontSize={11} /><YAxis tickFormatter={fmtK} fontSize={11} width={40} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} formatter={(v: number) => taka(v)} /><Legend /><Bar dataKey="revenue" name="Revenue" fill="#6366f1" radius={[3, 3, 0, 0]} /><Bar dataKey="expenses" name="Expenses" fill="#f59e0b" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div>}</Async>
                </Card>
                <Card title="Estimated profit trend (monthly)">
                  <Async state={monthly}>{(m) => <div className="h-64"><ResponsiveContainer><LineChart data={m}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" fontSize={11} /><YAxis tickFormatter={fmtK} fontSize={11} width={40} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} formatter={(v: number) => taka(v)} /><Line type="monotone" dataKey="estimated_profit" name="Est. profit" stroke="#059669" strokeWidth={2} dot /></LineChart></ResponsiveContainer></div>}</Async>
                </Card>
                <Card title="Top products (units sold)">
                  <div className="h-64"><ResponsiveContainer><BarChart data={d.top_products} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="name" width={130} fontSize={11} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} /><Bar dataKey="units_sold" name="Units" fill="#22d3ee" radius={[0, 3, 3, 0]} /></BarChart></ResponsiveContainer></div>
                </Card>
                <Card title="Category performance (30 days)">
                  <Async state={cats} empty={{ when: (c) => c.length === 0, message: "No category sales in the last 30 days." }}>{(c) => <div className="h-64"><ResponsiveContainer><BarChart data={c}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="category" fontSize={10} interval={0} angle={-15} textAnchor="end" height={55} /><YAxis tickFormatter={fmtK} fontSize={11} width={40} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} formatter={(v: number) => taka(v)} /><Legend /><Bar dataKey="revenue" name="Revenue" fill="#6366f1" /><Bar dataKey="gross_profit" name="Gross profit" fill="#10b981" /></BarChart></ResponsiveContainer></div>}</Async>
                </Card>
                <Card title="Inventory movement (30 days)">
                  <Async state={move} empty={{ when: (m) => m.length === 0, message: "No stock movements in the last 30 days." }}>{(m) => <div className="h-64"><ResponsiveContainer><BarChart data={m}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} fontSize={11} /><YAxis fontSize={11} width={40} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} /><Legend /><Bar dataKey="stock_in" name="Stock in" fill="#0ea5e9" /><Bar dataKey="stock_out" name="Stock out" fill="#ef4444" /></BarChart></ResponsiveContainer></div>}</Async>
                </Card>
              </div>

              <div className="grid gap-5 lg:grid-cols-3">
                <Card title="Business risks" action={<Link href="/alerts" className="text-xs text-indigo-300 hover:underline">All alerts</Link>} className="lg:col-span-2">
                  <Async state={risks}>{(r) => <ul className="space-y-3">{r.map((x) => (
                    <li key={x.risk} className="rounded-lg border p-3">
                      <div className="flex items-center gap-2"><Badge value={x.severity} /><span className="text-sm font-medium">{x.risk}</span></div>
                      <p className="mt-1 text-sm text-slate-300">{x.explanation}</p>
                      <p className="mt-1 text-xs text-slate-400">Investigate: {x.recommended_investigation}</p>
                    </li>))}</ul>}</Async>
                </Card>
                <div className="space-y-5">
                  <Card title="Business health (indicative)">
                    <Async state={health}>{(h) => <div>
                      <p className="text-3xl font-semibold">{h.overall_score}<span className="text-base text-slate-400">/100</span></p>
                      <ul className="mt-3 space-y-2">{h.components.map((c) => <li key={c.name} className="text-xs"><div className="flex justify-between"><span className="font-medium">{c.name}</span><span>{c.score}</span></div>
                        <div className="mt-1 h-1.5 rounded bg-slate-800"><div className="h-1.5 rounded bg-indigo-500" style={{ width: `${Math.min(100, c.score)}%` }} /></div><p className="mt-0.5 text-slate-400">{c.detail}</p></li>)}</ul>
                      <p className="mt-3 text-[11px] text-slate-400">{h.disclaimer}</p></div>}</Async>
                  </Card>
                  <Card title={`Unread alerts`}>
                    <Async state={alerts} empty={{ when: (a) => a.length === 0, message: "No unread alerts." }}>{(a) => <ul className="space-y-2">{a.slice(0, 5).map((x) => (
                      <li key={x.id} className="text-sm"><Badge value={x.severity} /> <span className="ml-1">{x.title}</span><p className="text-xs text-slate-400">{dateShort(x.created_at)}</p></li>))}</ul>}</Async>
                  </Card>
                </div>
              </div>
            </div>
          );
        }}
      </Async>
    </>
  );
}
