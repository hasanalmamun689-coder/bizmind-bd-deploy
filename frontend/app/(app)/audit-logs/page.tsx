"use client";
import { useState } from "react";
import { useFetch } from "@/hooks/useFetch";
import { useAuth } from "@/hooks/useAuth";
import { Async, Button, PageHeader, Table } from "@/components/ui";
import { dateTime, titleCase } from "@/lib/format";
import type { AuditLog, User } from "@/types";

export default function AuditLogsPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const owner = user?.role === "owner";
  const logs = useFetch<AuditLog[]>(owner ? "/api/audit-logs" : null, { page, page_size: 50 });
  const staff = useFetch<User[]>(owner ? "/api/employees" : null);
  if (!owner) return <p className="py-16 text-center text-sm text-slate-400">Only the business owner can view audit logs.</p>;
  const who = (id: string | null) => staff.data?.find((u) => u.id === id)?.full_name ?? (id ? "Former user" : "System");
  return (
    <>
      <PageHeader title="Audit logs" subtitle="Who did what, and when — including AI recommendation approvals and purchase drafts." />
      <Async state={logs} empty={{ when: (d) => d.length === 0, message: "No activity recorded yet." }}>{(rows) => <>
        <Table rows={rows} rowKey={(r) => r.id} cols={[
          { header: "When", cell: (r) => dateTime(r.created_at) }, { header: "User", cell: (r) => who(r.user_id) },
          { header: "Action", cell: (r) => <b>{titleCase(r.action.replace(".", " · "))}</b> }, { header: "Entity", cell: (r) => titleCase(r.entity_type), className: "hidden sm:table-cell" },
          { header: "Details", cell: (r) => <span className="text-xs text-slate-400">{r.log_metadata && Object.keys(r.log_metadata).length ? JSON.stringify(r.log_metadata) : "—"}</span>, className: "hidden md:table-cell max-w-xs truncate" }]} />
        <div className="mt-3 flex justify-end gap-2"><Button variant="secondary" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><Button variant="secondary" size="sm" disabled={rows.length < 50} onClick={() => setPage(page + 1)}>Next</Button></div></>}</Async>
    </>
  );
}
