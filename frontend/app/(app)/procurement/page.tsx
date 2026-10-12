"use client";
import { useState, FormEvent } from "react";
import { Plus } from "lucide-react";
import { useFetch } from "@/hooks/useFetch";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Field, Input, Modal, PageHeader, Select, Table, useToast } from "@/components/ui";
import { dateShort, taka, titleCase } from "@/lib/format";
import type { Product, PurchaseOrder, Supplier } from "@/types";

const NEXT: Record<string, string> = { draft: "pending_approval", approved: "ordered", ordered: "delivered", delivered: "completed" };
const NEXT_LABEL: Record<string, string> = { draft: "Submit for approval", approved: "Mark ordered", ordered: "Mark delivered", delivered: "Complete" };

export default function ProcurementPage() {
  const { user } = useAuth();
  const list = useFetch<PurchaseOrder[]>("/api/purchase-orders");
  const sups = useFetch<Supplier[]>("/api/suppliers");
  const products = useFetch<Product[]>("/api/products", { page_size: 200 });
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ supplier_id: "", product_id: "", quantity: "10", unit_price: "", delivery: "" });
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const sname = (id: string) => sups.data?.find((s) => s.id === id)?.name ?? "Supplier";
  const pname = (id: string) => products.data?.find((p) => p.id === id)?.name ?? "Product";

  async function act(fn: () => Promise<unknown>, ok: string) {
    try { await fn(); toast("success", ok); list.reload(); } catch (err) { toast("error", err instanceof ApiError ? err.message : "That action failed."); }
  }
  async function create(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    await act(() => api("/api/purchase-orders", { method: "POST", body: { supplier_id: f.supplier_id, expected_delivery_date: f.delivery || null, items: [{ product_id: f.product_id, quantity: +f.quantity, unit_price: +f.unit_price }] } }), "Purchase order draft created.");
    setBusy(false); setOpen(false);
  }
  const setStatus = (id: string, status: string) => act(() => api(`/api/purchase-orders/${id}/status`, { method: "PUT", body: { status } }), `Status changed to ${titleCase(status)}.`);

  return (
    <>
      <PageHeader title="Procurement" subtitle="Draft → Pending approval → Approved → Ordered → Delivered → Completed. Only the owner approves." action={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />New purchase order</Button>} />
      <Async state={list} empty={{ when: (d) => d.length === 0, message: "No purchase orders yet. Create one, or approve an AI recommendation to generate a draft." }}>
        {(rows) => <Table rows={rows} rowKey={(r) => r.id} cols={[
          { header: "Created", cell: (r) => dateShort(r.created_at) },
          { header: "Supplier", cell: (r) => <div><p className="font-medium">{sname(r.supplier_id)}</p>{r.source === "ai_recommendation" && <span className="text-xs text-violet-600">From AI recommendation</span>}</div> },
          { header: "Items", cell: (r) => <span className="text-slate-300">{r.items.map((i) => `${i.quantity}× ${pname(i.product_id)}`).join(", ")}</span>, className: "hidden md:table-cell" },
          { header: "Expected", cell: (r) => dateShort(r.expected_delivery_date), className: "hidden sm:table-cell" },
          { header: "Cost", cell: (r) => <b>{taka(r.total_cost)}</b>, className: "text-right" },
          { header: "Status", cell: (r) => <Badge value={r.status} /> },
          { header: "", cell: (r) => <div className="flex justify-end gap-1">
            {r.status === "pending_approval" && (user?.role === "owner" ? <Button size="sm" onClick={() => act(() => api(`/api/purchase-orders/${r.id}/approve`, { method: "POST" }), "Purchase order approved.")}>Approve</Button> : <span className="text-xs text-slate-400">Awaiting owner</span>)}
            {NEXT[r.status] && <Button size="sm" variant="secondary" onClick={() => setStatus(r.id, NEXT[r.status])}>{NEXT_LABEL[r.status]}</Button>}
            {["draft", "pending_approval", "approved", "ordered"].includes(r.status) && <Button size="sm" variant="ghost" onClick={() => confirm("Cancel this purchase order?") && setStatus(r.id, "cancelled")}>Cancel</Button>}
          </div> },
        ]} />}
      </Async>
      {open && <Modal title="New purchase order (draft)" onClose={() => setOpen(false)}><form onSubmit={create} className="space-y-3">
        <Field label="Supplier"><Select required value={f.supplier_id} onChange={(e) => setF({ ...f, supplier_id: e.target.value })}><option value="">Select…</option>{sups.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select></Field>
        <Field label="Product"><Select required value={f.product_id} onChange={(e) => { const p = products.data?.find((x) => x.id === e.target.value); setF({ ...f, product_id: e.target.value, unit_price: p ? String(p.purchase_price) : f.unit_price }); }}><option value="">Select…</option>{products.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="Quantity"><Input required type="number" min="1" value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} /></Field>
          <Field label="Unit price (৳)"><Input required type="number" min="0" step="0.01" value={f.unit_price} onChange={(e) => setF({ ...f, unit_price: e.target.value })} /></Field></div>
        <Field label="Expected delivery"><Input type="date" value={f.delivery} onChange={(e) => setF({ ...f, delivery: e.target.value })} /></Field>
        <p className="text-right text-sm">Expected cost: <b>{taka((+f.quantity || 0) * (+f.unit_price || 0))}</b></p>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" busy={busy}>Create draft</Button></div></form></Modal>}
    </>
  );
}
