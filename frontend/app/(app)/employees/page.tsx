"use client";
import { useState, FormEvent } from "react";
import { Plus } from "lucide-react";
import { useFetch } from "@/hooks/useFetch";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Field, Input, Modal, PageHeader, Select, Table, useToast } from "@/components/ui";
import type { User } from "@/types";

export default function EmployeesPage() {
  const { user } = useAuth();
  const list = useFetch<User[]>(user?.role === "owner" ? "/api/employees" : null);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ full_name: "", email: "", password: "", job_title: "", role: "manager" });
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  if (user?.role !== "owner") return <p className="py-16 text-center text-sm text-slate-400">Only the business owner can manage employees.</p>;

  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    try { await api("/api/employees", { method: "POST", body: { ...f, job_title: f.job_title || null } }); toast("success", "Employee added."); setOpen(false); setF({ full_name: "", email: "", password: "", job_title: "", role: "manager" }); list.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not add employee."); }
    finally { setBusy(false); }
  }
  return (
    <>
      <PageHeader title="Employees" subtitle="Owners have full access. Managers run daily operations but cannot approve purchase orders or view admin areas." action={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Add employee</Button>} />
      <Async state={list}>{(rows) => <Table rows={rows} rowKey={(r) => r.id} cols={[
        { header: "Name", cell: (r) => <div><p className="font-medium">{r.full_name}</p><p className="text-xs text-slate-400">{r.job_title ?? "—"}</p></div> },
        { header: "Email", cell: (r) => r.email }, { header: "Role", cell: (r) => <Badge value={r.role === "owner" ? "high-value" : "regular"} label={r.role} /> }]} />}</Async>
      {open && <Modal title="Add employee" onClose={() => setOpen(false)}><form onSubmit={submit} className="space-y-3">
        <Field label="Full name"><Input required minLength={2} value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
        <Field label="Email"><Input required type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Temporary password" hint="At least 8 characters."><Input required type="password" minLength={8} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        <div className="grid grid-cols-2 gap-3"><Field label="Job title"><Input value={f.job_title} onChange={(e) => setF({ ...f, job_title: e.target.value })} /></Field>
          <Field label="Role"><Select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="manager">Manager</option><option value="owner">Owner</option></Select></Field></div>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" busy={busy}>Add</Button></div></form></Modal>}
    </>
  );
}
