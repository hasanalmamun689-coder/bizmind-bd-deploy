"use client";
import { useEffect, useState, FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useFetch } from "@/hooks/useFetch";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Card, Field, Input, KpiCard, Modal, PageHeader, Select, Table, useToast } from "@/components/ui";
import { dateTime, taka } from "@/lib/format";
import type { Customer, Product, Sale, SalesSummary } from "@/types";

export default function SalesPage() {
  const [days, setDays] = useState("30");
  const [customerId, setCustomerId] = useState("");
  const [productId, setProductId] = useState("");
  const summary = useFetch<SalesSummary>("/api/sales/summary", { days });
  const sales = useFetch<Sale[]>("/api/sales", { customer_id: customerId, product_id: productId, page_size: 100 });
  const products = useFetch<Product[]>("/api/products", { page_size: 200 });
  const customers = useFetch<Customer[]>("/api/customers");
  const [open, setOpen] = useState(false);
  useEffect(() => { if (new URLSearchParams(window.location.search).get("new") === "1") setOpen(true); }, []);
  const [lines, setLines] = useState([{ product_id: "", quantity: "1" }]);
  const [cust, setCust] = useState("");
  const [pay, setPay] = useState("cash");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const pname = (id: string) => products.data?.find((p) => p.id === id)?.name ?? "Unknown product";
  const cname = (id: string | null) => (id ? customers.data?.find((c) => c.id === id)?.name ?? "Customer" : "Walk-in");

  const total = lines.reduce((s, l) => s + (products.data?.find((p) => p.id === l.product_id)?.selling_price ?? 0) * (+l.quantity || 0), 0);

  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    try {
      await api("/api/sales", { method: "POST", body: { customer_id: cust || null, payment_method: pay, items: lines.map((l) => ({ product_id: l.product_id, quantity: +l.quantity })) } });
      toast("success", "Sale recorded. Inventory updated."); setOpen(false); setLines([{ product_id: "", quantity: "1" }]); setCust("");
      sales.reload(); summary.reload(); products.reload();
    } catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not record the sale."); }
    finally { setBusy(false); }
  }

  async function cancelSale(s: Sale) {
    if (!confirm(`Cancel this ${taka(s.total_amount)} sale? Stock will be returned to inventory and the sale excluded from revenue.`)) return;
    try { await api(`/api/sales/${s.id}/cancel`, { method: "POST" }); toast("success", "Sale cancelled. Stock restored."); sales.reload(); summary.reload(); products.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not cancel the sale."); }
  }

  return (
    <>
      <PageHeader title="Sales" subtitle="Every sale updates inventory, analytics and forecasts." action={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />New sale</Button>} />
      <div className="mb-3 flex justify-end"><Select aria-label="Summary period" className="w-40" value={days} onChange={(e) => setDays(e.target.value)}><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option></Select></div>
      <Async state={summary}>{(s) => (
        <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label="Revenue" value={taka(s.total_revenue)} /><KpiCard label="Gross profit" value={taka(s.gross_profit)} tone="good" />
          <KpiCard label="Transactions" value={String(s.total_transactions)} /><KpiCard label="Avg order value" value={taka(s.average_order_value)} />
        </div>)}</Async>
      <div className="mb-4 flex flex-wrap gap-2">
        <Select aria-label="Filter by customer" className="w-52" value={customerId} onChange={(e) => setCustomerId(e.target.value)}><option value="">All customers</option>{customers.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select>
        <Select aria-label="Filter by product" className="w-52" value={productId} onChange={(e) => setProductId(e.target.value)}><option value="">All products</option>{products.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select>
      </div>
      <Async state={sales} empty={{ when: (d) => d.length === 0, message: customerId || productId ? "No sales match these filters." : "No sales yet. Record your first sale to see analytics and forecasts.", action: <Button onClick={() => setOpen(true)}>Record a sale</Button> }}>
        {(rows) => <Table rows={rows} rowKey={(r) => r.id} cols={[
          { header: "Date", cell: (r) => dateTime(r.created_at) },
          { header: "Customer", cell: (r) => cname(r.customer_id), className: "hidden sm:table-cell" },
          { header: "Items", cell: (r) => <span className="text-slate-300">{r.items.map((i) => `${i.quantity}× ${pname(i.product_id)}`).join(", ")}</span> },
          { header: "Payment", cell: (r) => <Badge value="regular" label={r.payment_method} />, className: "hidden md:table-cell" },
          { header: "Total", cell: (r) => <b>{taka(r.total_amount)}</b>, className: "text-right" },
          { header: "Profit", cell: (r) => taka(r.gross_profit), className: "text-right hidden sm:table-cell" },
          { header: "", cell: (r) => r.status === "cancelled" ? <Badge value="cancelled" /> : <Button size="sm" variant="ghost" onClick={() => cancelSale(r)}>Cancel sale</Button> },
        ]} />}
      </Async>

      {open && <Modal title="Record sale" onClose={() => setOpen(false)}>
        <form onSubmit={submit} className="space-y-3">
          {lines.map((l, i) => (
            <div key={i} className="flex items-end gap-2">
              <div className="flex-1"><Field label={i === 0 ? "Product" : ""}><Select required value={l.product_id} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, product_id: e.target.value } : x)))}>
                <option value="">Select…</option>{products.data?.filter((p) => p.is_active).map((p) => <option key={p.id} value={p.id}>{p.name} ({p.current_stock} in stock)</option>)}</Select></Field></div>
              <div className="w-20"><Field label={i === 0 ? "Qty" : ""}><Input required type="number" min="1" value={l.quantity} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, quantity: e.target.value } : x)))} /></Field></div>
              {lines.length > 1 && <button type="button" aria-label="Remove line" className="mb-2 rounded p-1.5 text-slate-400 hover:bg-slate-800" onClick={() => setLines(lines.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></button>}
            </div>))}
          <Button type="button" size="sm" variant="secondary" onClick={() => setLines([...lines, { product_id: "", quantity: "1" }])}>+ Add another item</Button>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Customer (optional)"><Select value={cust} onChange={(e) => setCust(e.target.value)}><option value="">Walk-in</option>{customers.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>
            <Field label="Payment"><Select value={pay} onChange={(e) => setPay(e.target.value)}><option value="cash">Cash</option><option value="bkash">bKash</option><option value="card">Card</option></Select></Field>
          </div>
          <p className="text-right text-sm text-slate-300">Total: <b className="text-lg text-white">{taka(total)}</b></p>
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" busy={busy}>Record sale</Button></div>
        </form></Modal>}
    </>
  );
}
