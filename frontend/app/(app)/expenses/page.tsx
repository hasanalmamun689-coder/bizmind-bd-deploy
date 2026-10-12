"use client";
import { useState, FormEvent } from "react";
import { Plus } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { useFetch } from "@/hooks/useFetch";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Card, Field, Input, Modal, PageHeader, Select, Table, useToast } from "@/components/ui";
import { dateShort, taka, titleCase } from "@/lib/format";
import type { Expense, ExpenseSummary } from "@/types";

const CATS = ["rent", "salary", "electricity", "transportation", "marketing", "maintenance", "procurement", "other"];
const COLORS = ["#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#ef4444", "#0ea5e9", "#64748b", "#ec4899"];
const today = () => new Date().toISOString().slice(0, 10);

export default function ExpensesPage() {
  const { user } = useAuth();
  const [category, setCategory] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const list = useFetch<Expense[]>("/api/expenses", { category, date_from: from, date_to: to, page_size: 200 });
  const summary = useFetch<ExpenseSummary>("/api/expenses/summary");
  const [editing, setEditing] = useState<Expense | "new" | null>(null);
  const [f, setF] = useState({ category: "rent", amount: "", description: "", expense_date: today() });
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const openForm = (e: Expense | "new") => { setEditing(e); setF(e === "new" ? { category: "rent", amount: "", description: "", expense_date: today() } : { category: e.category, amount: String(e.amount), description: e.description ?? "", expense_date: e.expense_date }); };
  const refresh = () => { list.reload(); summary.reload(); };
  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    const body = { category: f.category, amount: +f.amount, description: f.description || null, expense_date: f.expense_date };
    try { editing === "new" ? await api("/api/expenses", { method: "POST", body }) : await api(`/api/expenses/${(editing as Expense).id}`, { method: "PUT", body });
      toast("success", "Expense saved."); setEditing(null); refresh(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not save the expense."); }
    finally { setBusy(false); }
  }
  async function remove(x: Expense) {
    if (!confirm("Delete this expense? This is recorded in the audit log.")) return;
    try { await api(`/api/expenses/${x.id}`, { method: "DELETE" }); toast("success", "Expense deleted."); refresh(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not delete."); }
  }

  return (
    <>
      <PageHeader title="Expenses" subtitle="Track operating costs; unusual months are flagged in Alerts." action={<Button onClick={() => openForm("new")}><Plus className="h-4 w-4" />Add expense</Button>} />
      <Async state={summary} empty={{ when: (s) => s.monthly.length === 0, message: "No expenses recorded yet." }}>{(s) => (
        <div className="mb-5 grid gap-5 lg:grid-cols-2">
          <Card title="Monthly expenses"><div className="h-56"><ResponsiveContainer><BarChart data={s.monthly}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" fontSize={11} /><YAxis fontSize={11} width={45} tickFormatter={(v) => `${Math.round(v / 1000)}k`} /><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} formatter={(v: number) => taka(v)} /><Bar dataKey="total" name="Expenses" fill="#f59e0b" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div></Card>
          <Card title="By category (all time)"><div className="h-56"><ResponsiveContainer><PieChart><Pie data={Object.entries(s.by_category).map(([name, value]) => ({ name: titleCase(name), value }))} dataKey="value" nameKey="name" outerRadius={80}>{Object.keys(s.by_category).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 10, color: "#e2e8f0" }} itemStyle={{ color: "#e2e8f0" }} labelStyle={{ color: "#94a3b8" }} formatter={(v: number) => taka(v)} /><Legend /></PieChart></ResponsiveContainer></div></Card>
        </div>)}</Async>
      <div className="mb-4 flex flex-wrap gap-2">
        <Select aria-label="Category" className="w-44" value={category} onChange={(e) => setCategory(e.target.value)}><option value="">All categories</option>{CATS.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}</Select>
        <Input aria-label="From date" type="date" className="w-40" value={from} onChange={(e) => setFrom(e.target.value)} /><Input aria-label="To date" type="date" className="w-40" value={to} onChange={(e) => setTo(e.target.value)} />
      </div>
      <Async state={list} empty={{ when: (d) => d.length === 0, message: category || from || to ? "No expenses match these filters." : "No expenses yet. Add your first expense.", action: <Button onClick={() => openForm("new")}>Add expense</Button> }}>
        {(rows) => <Table rows={rows} rowKey={(r) => r.id} cols={[
          { header: "Date", cell: (r) => dateShort(r.expense_date) }, { header: "Category", cell: (r) => <Badge value="regular" label={titleCase(r.category)} /> },
          { header: "Description", cell: (r) => r.description ?? "—", className: "hidden sm:table-cell" }, { header: "Amount", cell: (r) => <b>{taka(r.amount)}</b>, className: "text-right" },
          { header: "", cell: (r) => <div className="flex justify-end gap-1"><Button size="sm" variant="secondary" onClick={() => openForm(r)}>Edit</Button>{user?.role === "owner" && <Button size="sm" variant="ghost" onClick={() => remove(r)}>Delete</Button>}</div> },
        ]} />}
      </Async>
      {editing && <Modal title={editing === "new" ? "Add expense" : "Edit expense"} onClose={() => setEditing(null)}><form onSubmit={save} className="space-y-3">
        <Field label="Category"><Select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{CATS.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}</Select></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="Amount (৳)"><Input required type="number" min="1" step="0.01" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></Field><Field label="Date"><Input required type="date" value={f.expense_date} onChange={(e) => setF({ ...f, expense_date: e.target.value })} /></Field></div>
        <Field label="Description"><Input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" busy={busy}>Save</Button></div></form></Modal>}
    </>
  );
}
