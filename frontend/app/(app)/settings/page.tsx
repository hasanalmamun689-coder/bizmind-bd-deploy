"use client";
import { useEffect, useState, FormEvent } from "react";
import { useFetch } from "@/hooks/useFetch";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError } from "@/lib/api";
import { Async, Badge, Button, Card, Field, Input, PageHeader, useToast } from "@/components/ui";

interface SettingsView { business: { name: string; industry: string | null; address: string | null; currency: string }; system: { environment: string; ai_provider: string; ai_mode: string } }

export default function SettingsPage() {
  const { user } = useAuth();
  const s = useFetch<SettingsView>(user?.role === "owner" ? "/api/settings" : null);
  const [f, setF] = useState({ name: "", industry: "", address: "" });
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  useEffect(() => { if (s.data) setF({ name: s.data.business.name, industry: s.data.business.industry ?? "", address: s.data.business.address ?? "" }); }, [s.data]);
  if (user?.role !== "owner") return <p className="py-16 text-center text-sm text-slate-400">Only the business owner can change settings.</p>;

  async function save(e: FormEvent) {
    e.preventDefault(); setBusy(true);
    try { await api("/api/settings/business", { method: "PUT", body: { name: f.name, industry: f.industry || null, address: f.address || null } }); toast("success", "Settings saved."); s.reload(); }
    catch (err) { toast("error", err instanceof ApiError ? err.message : "Could not save settings."); }
    finally { setBusy(false); }
  }
  return (
    <>
      <PageHeader title="Settings" subtitle="Business profile and system status." />
      <Async state={s}>{(d) => (
        <div className="grid gap-5 lg:grid-cols-2">
          <Card title="Business profile"><form onSubmit={save} className="space-y-3">
            <Field label="Business name"><Input required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
            <Field label="Industry"><Input value={f.industry} onChange={(e) => setF({ ...f, industry: e.target.value })} /></Field>
            <Field label="Address"><Input value={f.address} onChange={(e) => setF({ ...f, address: e.target.value })} /></Field>
            <Field label="Currency" hint="Fixed to Bangladeshi Taka (৳) in this version."><Input disabled value={d.business.currency} /></Field>
            <Button type="submit" busy={busy}>Save changes</Button></form></Card>
          <Card title="System status">
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between"><dt className="text-slate-400">Environment</dt><dd className="font-medium capitalize">{d.system.environment}</dd></div>
              <div className="flex items-center justify-between"><dt className="text-slate-400">AI assistant mode</dt><dd><Badge value={d.system.ai_mode === "live_model" ? "approved" : "draft"} label={d.system.ai_mode === "live_model" ? `Live model (${d.system.ai_provider})` : "Data-only (no AI provider configured)"} /></dd></div>
            </dl>
            <p className="mt-4 text-xs text-slate-400">AI provider and keys are set on the server through environment variables (AI_PROVIDER, AI_API_KEY) and are never shown or stored in the browser.</p>
          </Card>
        </div>)}</Async>
    </>
  );
}
