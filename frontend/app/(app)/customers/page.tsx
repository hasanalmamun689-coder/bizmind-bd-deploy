"use client";
import { useState, FormEvent } from "react";
import { Plus } from "lucide-react";
import { useFetch } from "@/hooks/useFetch";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Field, Input, Modal, PageHeader, Select, Table, useToast } from "@/components/ui";
import { dateShort, taka } from "@/lib/format";
import type { Customer } from "@/types";

export default function CustomersPage() {
  const list = useFetch<Customer[]>("/api/customers");
  const [seg, setSeg] = useState("");
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", contact: "" });
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    try { await api("/api/customers", { method: "POST", body: { name: f.name, contact: f.contact || null } }); toast("success", "Customer added."); setOpen(false); setF({ name: "", contact: "" }); list.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not add customer."); }
    finally { setBusy(false); }
  }
  return (
    <>
      <PageHeader title="Customers" subtitle="Segments are simple rules (orders, spend, recency) — a guide, not a scientific classification." action={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Add customer</Button>} />
      <div className="mb-4"><Select aria-label="Filter by segment" className="w-48" value={seg} onChange={(e) => setSeg(e.target.value)}><option value="">All segments</option>{["new", "regular", "high-value", "inactive"].map((s) => <option key={s} value={s}>{s}</option>)}</Select></div>
      <Async state={list} empty={{ when: (d) => d.length === 0, message: "No customers yet. Add customers to track purchase behavior." }}>
        {(all) => { const rows = all.filter((c) => !seg || c.segment === seg); return rows.length === 0 ? <p className="py-10 text-center text-sm text-slate-400">No customers in this segment.</p> :
          <Table rows={rows} rowKey={(r) => r.id} cols={[
            { header: "Customer", cell: (r) => <div><p className="font-medium">{r.name}</p><p className="text-xs text-slate-400">{r.contact ?? "—"}</p></div> },
            { header: "Orders", cell: (r) => r.total_orders, className: "text-right" },
            { header: "Total spent", cell: (r) => taka(r.total_spent), className: "text-right" },
            { header: "Last purchase", cell: (r) => dateShort(r.last_purchase_at), className: "hidden sm:table-cell" },
            { header: "Segment", cell: (r) => <Badge value={r.segment} /> },
          ]} />; }}
      </Async>
      {open && <Modal title="Add customer" onClose={() => setOpen(false)}><form onSubmit={submit} className="space-y-3">
        <Field label="Name"><Input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Contact"><Input value={f.contact} onChange={(e) => setF({ ...f, contact: e.target.value })} /></Field>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" busy={busy}>Save</Button></div></form></Modal>}
    </>
  );
}
