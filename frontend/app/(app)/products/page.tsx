"use client";
import { useState, FormEvent } from "react";
import { Plus, Search } from "lucide-react";
import { useFetch } from "@/hooks/useFetch";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Field, Input, Modal, PageHeader, Select, Table, useToast } from "@/components/ui";
import { taka } from "@/lib/format";
import type { Category, Product, Supplier } from "@/types";

const blank = { name: "", sku: "", brand: "", unit: "pcs", purchase_price: "", selling_price: "", current_stock: "0", minimum_stock: "0", maximum_stock: "0", category_id: "", supplier_id: "", expiry_date: "" };

export default function ProductsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const list = useFetch<Product[]>("/api/products", { search, status, page_size: 200 });
  const cats = useFetch<Category[]>("/api/products/meta/categories");
  const sups = useFetch<Supplier[]>("/api/suppliers");
  const [editing, setEditing] = useState<Product | "new" | null>(null);
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const open = (p: Product | "new") => {
    setEditing(p);
    setF(p === "new" ? blank : { name: p.name, sku: p.sku, brand: p.brand ?? "", unit: p.unit, purchase_price: String(p.purchase_price), selling_price: String(p.selling_price), current_stock: String(p.current_stock), minimum_stock: String(p.minimum_stock), maximum_stock: String(p.maximum_stock), category_id: p.category_id ?? "", supplier_id: p.supplier_id ?? "", expiry_date: p.expiry_date ?? "" });
  };

  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    const body: Record<string, unknown> = { name: f.name, brand: f.brand || null, unit: f.unit, purchase_price: +f.purchase_price, selling_price: +f.selling_price, minimum_stock: +f.minimum_stock, maximum_stock: +f.maximum_stock, category_id: f.category_id || null, supplier_id: f.supplier_id || null, expiry_date: f.expiry_date || null };
    try {
      if (editing === "new") await api("/api/products", { method: "POST", body: { ...body, sku: f.sku, current_stock: +f.current_stock } });
      else if (editing) await api(`/api/products/${editing.id}`, { method: "PUT", body });
      toast("success", editing === "new" ? "Product added." : "Product updated."); setEditing(null); list.reload();
    } catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not save the product."); }
    finally { setBusy(false); }
  }
  async function archive(p: Product) {
    if (!confirm(`Archive "${p.name}"? Its sales history will be kept.`)) return;
    try { await api(`/api/products/${p.id}`, { method: "DELETE" }); toast("success", "Product archived."); list.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not archive."); }
  }
  const set = (k: keyof typeof blank) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  const catName = (id: string | null) => cats.data?.find((c) => c.id === id)?.name ?? "—";
  const supName = (id: string | null) => sups.data?.find((s) => s.id === id)?.name ?? "—";

  return (
    <>
      <PageHeader title="Products" subtitle="Catalog, pricing, margins and stock thresholds." action={<Button onClick={() => open("new")}><Plus className="h-4 w-4" />Add product</Button>} />
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-[200px] flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" aria-hidden /><Input aria-label="Search products" className="pl-9" placeholder="Search by name…" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
        <Select aria-label="Filter by status" className="w-44" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>{["healthy", "low_stock", "critical", "out_of_stock", "overstock"].map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </Select>
      </div>
      <Async state={list} empty={{ when: (d) => d.length === 0, message: search || status ? "No products match your filters." : "No products yet. Add your first product to start tracking inventory.", action: !search && !status ? <Button onClick={() => open("new")}>Add product</Button> : undefined }}>
        {(rows) => <Table rows={rows} rowKey={(r) => r.id} cols={[
          { header: "Product", cell: (r) => <div><p className="font-medium">{r.name}</p><p className="text-xs text-slate-400">{r.sku} · {catName(r.category_id)}</p></div> },
          { header: "Supplier", cell: (r) => supName(r.supplier_id), className: "hidden md:table-cell" },
          { header: "Buy", cell: (r) => taka(r.purchase_price), className: "text-right hidden sm:table-cell" },
          { header: "Sell", cell: (r) => taka(r.selling_price), className: "text-right" },
          { header: "Margin", cell: (r) => <span title={`Profit/unit ${taka(r.profit_per_unit)}`}>{r.margin_percent}%</span>, className: "text-right" },
          { header: "Stock", cell: (r) => <span>{r.current_stock} <span className="text-xs text-slate-400">/ min {r.minimum_stock}</span></span>, className: "text-right" },
          { header: "Status", cell: (r) => <Badge value={r.status} /> },
          { header: "", cell: (r) => <div className="flex justify-end gap-1"><Button size="sm" variant="secondary" onClick={() => open(r)}>Edit</Button><Button size="sm" variant="ghost" onClick={() => archive(r)}>Archive</Button></div> },
        ]} />}
      </Async>

      {editing && (
        <Modal title={editing === "new" ? "Add product" : "Edit product"} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="grid grid-cols-2 gap-3">
            <div className="col-span-2"><Field label="Name"><Input required value={f.name} onChange={set("name")} /></Field></div>
            <Field label="SKU"><Input required disabled={editing !== "new"} value={f.sku} onChange={set("sku")} /></Field>
            <Field label="Brand"><Input value={f.brand} onChange={set("brand")} /></Field>
            <Field label="Category"><Select value={f.category_id} onChange={set("category_id")}><option value="">—</option>{cats.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>
            <Field label="Supplier"><Select value={f.supplier_id} onChange={set("supplier_id")}><option value="">—</option>{sups.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select></Field>
            <Field label="Purchase price (৳)"><Input required type="number" min="0" step="0.01" value={f.purchase_price} onChange={set("purchase_price")} /></Field>
            <Field label="Selling price (৳)"><Input required type="number" min="0" step="0.01" value={f.selling_price} onChange={set("selling_price")} /></Field>
            <Field label="Unit"><Input value={f.unit} onChange={set("unit")} /></Field>
            <Field label="Expiry date"><Input type="date" value={f.expiry_date} onChange={set("expiry_date")} /></Field>
            {editing === "new" && <Field label="Opening stock"><Input type="number" min="0" value={f.current_stock} onChange={set("current_stock")} /></Field>}
            <Field label="Minimum stock"><Input type="number" min="0" value={f.minimum_stock} onChange={set("minimum_stock")} /></Field>
            <Field label="Maximum stock"><Input type="number" min="0" value={f.maximum_stock} onChange={set("maximum_stock")} /></Field>
            <div className="col-span-2 flex justify-end gap-2 pt-2"><Button type="button" variant="secondary" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit" busy={busy}>Save</Button></div>
          </form>
        </Modal>
      )}
    </>
  );
}
