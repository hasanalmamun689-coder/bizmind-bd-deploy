"use client";
import { useState, FormEvent } from "react";
import { Plus } from "lucide-react";
import { useFetch } from "@/hooks/useFetch";
import { api, ApiError } from "@/lib/api";
import { Async, Button, Card, Field, Input, Modal, PageHeader, Select, Table, useToast } from "@/components/ui";
import { taka } from "@/lib/format";
import type { Product, Supplier, SupplierComparison } from "@/types";

const Meter = ({ v }: { v: number }) => <div className="flex items-center gap-2"><div className="h-1.5 w-16 rounded bg-slate-800"><div className={`h-1.5 rounded ${v >= 80 ? "bg-emerald-500" : v >= 60 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${v}%` }} /></div><span className="text-xs">{v}</span></div>;

export default function SuppliersPage() {
  const list = useFetch<Supplier[]>("/api/suppliers");
  const products = useFetch<Product[]>("/api/products", { page_size: 200 });
  const [pid, setPid] = useState("");
  const cmp = useFetch<SupplierComparison[]>(pid ? "/api/suppliers/compare" : null, { product_id: pid });
  const [open, setOpen] = useState(false);
  const [priceFor, setPriceFor] = useState<Supplier | null>(null);
  const [pf, setPf] = useState({ product_id: "", price: "", moq: "1" });
  const [f, setF] = useState({ name: "", contact: "", location: "", delivery_time_days: "3", reliability_score: "80", quality_score: "80", fulfillment_rate: "95", payment_terms: "" });
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    try { await api("/api/suppliers", { method: "POST", body: { ...f, delivery_time_days: +f.delivery_time_days, reliability_score: +f.reliability_score, quality_score: +f.quality_score, fulfillment_rate: +f.fulfillment_rate, contact: f.contact || null, location: f.location || null, payment_terms: f.payment_terms || null } });
      toast("success", "Supplier added."); setOpen(false); list.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not add supplier."); }
    finally { setBusy(false); }
  }
  async function savePrice(e: FormEvent) {
    e.preventDefault(); if (!priceFor) return; setBusy(true);
    try { await api(`/api/suppliers/${priceFor.id}/prices`, { method: "PUT", body: { product_id: pf.product_id, price: +pf.price, minimum_order_quantity: +pf.moq } });
      toast("success", "Price saved (kept in price history)."); setPriceFor(null); if (pid) cmp.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not save the price."); }
    finally { setBusy(false); }
  }
  return (
    <>
      <PageHeader title="Suppliers" subtitle="Compare on price, delivery, reliability, quality and fulfillment — evidence, not one hidden score." action={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Add supplier</Button>} />
      <Card title="Compare suppliers for a product" className="mb-5">
        <Select aria-label="Product to compare" value={pid} onChange={(e) => setPid(e.target.value)} className="max-w-sm"><option value="">Select a product…</option>{products.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select>
        {pid && <div className="mt-4"><Async state={cmp} empty={{ when: (d) => d.length === 0, message: "No supplier has a price recorded for this product yet." }}>{(rows) =>
          <Table rows={rows} rowKey={(r) => r.supplier.id} cols={[
            { header: "Supplier", cell: (r) => <b>{r.supplier.name}</b> },
            { header: "Price", cell: (r) => taka(r.price), className: "text-right" },
            { header: "MOQ", cell: (r) => r.minimum_order_quantity, className: "text-right" },
            { header: "Delivery", cell: (r) => `${r.supplier.delivery_time_days} days` },
            { header: "Reliability", cell: (r) => <Meter v={r.supplier.reliability_score} /> },
            { header: "Quality", cell: (r) => <Meter v={r.supplier.quality_score} />, className: "hidden md:table-cell" },
            { header: "Fulfillment", cell: (r) => `${r.supplier.fulfillment_rate}%`, className: "hidden md:table-cell" },
            { header: "Terms", cell: (r) => r.supplier.payment_terms ?? "—", className: "hidden lg:table-cell" },
          ]} />}</Async></div>}
      </Card>
      <Async state={list} empty={{ when: (d) => d.length === 0, message: "No suppliers yet. Add a supplier to start procurement." }}>
        {(rows) => <Table rows={rows} rowKey={(r) => r.id} cols={[
          { header: "Supplier", cell: (r) => <div><p className="font-medium">{r.name}</p><p className="text-xs text-slate-400">{r.location ?? "—"}</p></div> },
          { header: "Contact", cell: (r) => r.contact ?? "—", className: "hidden sm:table-cell" },
          { header: "Delivery", cell: (r) => `${r.delivery_time_days}d` },
          { header: "Reliability", cell: (r) => <Meter v={r.reliability_score} /> },
          { header: "Quality", cell: (r) => <Meter v={r.quality_score} />, className: "hidden md:table-cell" },
          { header: "Fulfillment", cell: (r) => `${r.fulfillment_rate}%`, className: "hidden md:table-cell" },
          { header: "Payment terms", cell: (r) => r.payment_terms ?? "—", className: "hidden lg:table-cell" },
          { header: "", cell: (r) => <Button size="sm" variant="secondary" onClick={() => { setPriceFor(r); setPf({ product_id: "", price: "", moq: "1" }); }}>Set price</Button> },
        ]} />}
      </Async>
      {priceFor && <Modal title={`Set product price — ${priceFor.name}`} onClose={() => setPriceFor(null)}><form onSubmit={savePrice} className="space-y-3">
        <Field label="Product"><Select required value={pf.product_id} onChange={(e) => setPf({ ...pf, product_id: e.target.value })}><option value="">Select…</option>{products.data?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</Select></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="Quoted price (৳)"><Input required type="number" min="0" step="0.01" value={pf.price} onChange={(e) => setPf({ ...pf, price: e.target.value })} /></Field>
          <Field label="Minimum order qty"><Input required type="number" min="1" value={pf.moq} onChange={(e) => setPf({ ...pf, moq: e.target.value })} /></Field></div>
        <p className="text-xs text-slate-400">Every change is recorded so price increases can be detected in Alerts.</p>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setPriceFor(null)}>Cancel</Button><Button type="submit" busy={busy}>Save price</Button></div></form></Modal>}
      {open && <Modal title="Add supplier" onClose={() => setOpen(false)}><form onSubmit={submit} className="grid grid-cols-2 gap-3">
        <div className="col-span-2"><Field label="Name"><Input required value={f.name} onChange={set("name")} /></Field></div>
        <Field label="Contact"><Input value={f.contact} onChange={set("contact")} /></Field><Field label="Location"><Input value={f.location} onChange={set("location")} /></Field>
        <Field label="Delivery (days)"><Input type="number" min="0" value={f.delivery_time_days} onChange={set("delivery_time_days")} /></Field><Field label="Payment terms"><Input value={f.payment_terms} onChange={set("payment_terms")} /></Field>
        <Field label="Reliability (0-100)"><Input type="number" min="0" max="100" value={f.reliability_score} onChange={set("reliability_score")} /></Field>
        <Field label="Quality (0-100)"><Input type="number" min="0" max="100" value={f.quality_score} onChange={set("quality_score")} /></Field>
        <Field label="Fulfillment % (0-100)"><Input type="number" min="0" max="100" value={f.fulfillment_rate} onChange={set("fulfillment_rate")} /></Field>
        <div className="col-span-2 flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" busy={busy}>Save</Button></div></form></Modal>}
    </>
  );
}
