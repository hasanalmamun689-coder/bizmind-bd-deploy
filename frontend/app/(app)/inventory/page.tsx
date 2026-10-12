"use client";
import { useState, FormEvent } from "react";
import { useFetch } from "@/hooks/useFetch";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Card, Field, Input, Modal, PageHeader, Select, Table, useToast } from "@/components/ui";
import { dateTime, titleCase } from "@/lib/format";
import type { InventoryTxn, Product } from "@/types";

export default function InventoryPage() {
  const [status, setStatus] = useState("");
  const list = useFetch<Product[]>("/api/inventory");
  const [adjust, setAdjust] = useState<Product | null>(null);
  const [history, setHistory] = useState<Product | null>(null);
  const [f, setF] = useState({ type: "stock_in", direction: "increase", quantity: "1", reason: "" });
  const [busy, setBusy] = useState(false);
  const hist = useFetch<InventoryTxn[]>(history ? `/api/inventory/${history.id}/history` : null);
  const toast = useToast();

  async function submit(e: FormEvent) {
    e.preventDefault(); if (!adjust) return; setBusy(true);
    try {
      await api("/api/inventory/adjust", { method: "POST", body: { product_id: adjust.id, type: f.type, direction: f.direction, quantity: +f.quantity, reason: f.reason || null } });
      toast("success", "Stock updated."); setAdjust(null); list.reload();
    } catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not update stock."); }
    finally { setBusy(false); }
  }
  const rows = (list.data ?? []).filter((p) => !status || p.status === status);
  const daysLeftHint = (p: Product) => (p.current_stock < p.minimum_stock ? `${p.minimum_stock - p.current_stock} below minimum` : "");

  return (
    <>
      <PageHeader title="Inventory" subtitle="Live stock levels, movements and adjustments." action={
        <Select aria-label="Filter by status" className="w-44" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>{["healthy", "low_stock", "critical", "out_of_stock", "overstock"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</Select>} />
      <Async state={list} empty={{ when: (d) => d.length === 0, message: "No inventory yet. Add products first." }}>
        {() => rows.length === 0 ? <p className="py-10 text-center text-sm text-slate-400">No products with this status.</p> :
          <Table rows={rows} rowKey={(r) => r.id} cols={[
            { header: "Product", cell: (r) => <div><p className="font-medium">{r.name}</p><p className="text-xs text-slate-400">{r.sku}</p></div> },
            { header: "Stock", cell: (r) => <div><b>{r.current_stock}</b> <span className="text-xs text-slate-400">{r.unit}</span><p className="text-xs text-amber-400">{daysLeftHint(r)}</p></div>, className: "text-right" },
            { header: "Min / Max", cell: (r) => `${r.minimum_stock} / ${r.maximum_stock}`, className: "text-right hidden sm:table-cell" },
            { header: "Expiry", cell: (r) => r.expiry_date ?? "—", className: "hidden md:table-cell" },
            { header: "Status", cell: (r) => <Badge value={r.status} /> },
            { header: "", cell: (r) => <div className="flex justify-end gap-1"><Button size="sm" variant="secondary" onClick={() => { setAdjust(r); setF({ type: "stock_in", direction: "increase", quantity: "1", reason: "" }); }}>Adjust</Button><Button size="sm" variant="ghost" onClick={() => setHistory(r)}>History</Button></div> },
          ]} />}
      </Async>

      {adjust && <Modal title={`Adjust stock — ${adjust.name}`} onClose={() => setAdjust(null)}>
        <form onSubmit={submit} className="space-y-3">
          <p className="text-sm text-slate-400">Current stock: <b>{adjust.current_stock}</b></p>
          <Field label="Movement"><Select value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}><option value="stock_in">Stock in (add)</option><option value="stock_out">Stock out (remove)</option><option value="adjustment">Manual correction (stock count)</option></Select></Field>
          {f.type === "adjustment" && <Field label="Correction direction"><Select value={f.direction} onChange={(e) => setF({ ...f, direction: e.target.value })}><option value="increase">Count is higher — add</option><option value="decrease">Count is lower — remove</option></Select></Field>}
          <Field label="Quantity"><Input type="number" min="1" required value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} /></Field>
          <Field label="Reason"><Input placeholder="e.g. Supplier delivery, damaged goods" value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field>
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setAdjust(null)}>Cancel</Button><Button type="submit" busy={busy}>Save</Button></div>
        </form></Modal>}

      {history && <Modal title={`Movement history — ${history.name}`} onClose={() => setHistory(null)}>
        <Async state={hist} empty={{ when: (d) => d.length === 0, message: "No movements recorded." }}>{(h) =>
          <ul className="divide-y text-sm">{h.map((t) => <li key={t.id} className="flex items-center justify-between py-2"><div><p className="font-medium">{titleCase(t.type)}</p><p className="text-xs text-slate-400">{dateTime(t.created_at)}{t.reason ? ` · ${t.reason}` : ""}</p></div>
            <div className="text-right"><p className={t.quantity_delta < 0 ? "text-rose-400" : "text-emerald-400"}>{t.quantity_delta > 0 ? "+" : ""}{t.quantity_delta}</p><p className="text-xs text-slate-400">→ {t.resulting_stock}</p></div></li>)}</ul>}</Async></Modal>}
    </>
  );
}
