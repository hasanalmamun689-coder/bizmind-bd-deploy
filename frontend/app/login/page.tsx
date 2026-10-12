"use client";
import { useState, FormEvent } from "react";
import Link from "next/link";
import { Brand } from "@/components/Brand";
import { useAuth } from "@/hooks/useAuth";
import { Button, Field, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [f, setF] = useState({ email: "", password: "", full_name: "", business_name: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault(); setError(null); setBusy(true);
    try { mode === "login" ? await login(f.email, f.password) : await register(f); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again."); }
    finally { setBusy(false); }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,#1e1b4b_0%,#0b0f19_60%)] p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl shadow-black/40 backdrop-blur sm:p-8">
        <Link href="/" aria-label="BizMind BD – go to home page" className="inline-block"><Brand size="lg" /></Link>
        <p className="mt-3 text-sm text-slate-400">Understand your business. Decide with data. Stay in control.</p>
        <Link href="/" className="mt-4 inline-block text-xs text-slate-400 hover:text-white">← Back to home</Link>
        <form onSubmit={submit} className="mt-6 space-y-4">
          {mode === "register" && <>
            <Field label="Business name"><Input required minLength={2} value={f.business_name} onChange={set("business_name")} /></Field>
            <Field label="Your full name"><Input required minLength={2} value={f.full_name} onChange={set("full_name")} /></Field>
          </>}
          <Field label="Email"><Input type="email" required autoComplete="email" value={f.email} onChange={set("email")} /></Field>
          <Field label="Password" hint={mode === "register" ? "At least 8 characters." : undefined}>
            <Input type="password" required minLength={mode === "register" ? 8 : 1} autoComplete={mode === "login" ? "current-password" : "new-password"} value={f.password} onChange={set("password")} />
          </Field>
          {error && <p role="alert" className="rounded-lg bg-rose-500/10 px-3 py-2 text-sm text-rose-300">{error}</p>}
          <Button type="submit" busy={busy} className="w-full">{mode === "login" ? "Sign in" : "Create account"}</Button>
        </form>
        <button className="mt-4 w-full text-center text-sm text-indigo-300 hover:underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
          {mode === "login" ? "New here? Create a business account" : "Already have an account? Sign in"}
        </button>
        {mode === "login" && <p className="mt-4 rounded-lg bg-slate-950/60 p-3 text-xs text-slate-400">Demo data: <b>owner@demo.bd</b> or <b>manager@demo.bd</b> · password <b>Demo@1234</b></p>}
      </div>
    </div>
  );
}
