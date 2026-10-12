"use client";
import Link from "next/link";
import { ArrowRight, BarChart3, Bot, Boxes, LineChart, ShieldCheck, Sparkles, Truck } from "lucide-react";
import { Brand } from "@/components/Brand";
import { useAuth } from "@/hooks/useAuth";

const FEATURES = [
  { icon: BarChart3, title: "Business analytics", text: "Sales, profit and expense trends in one clear view, built from your real records." },
  { icon: LineChart, title: "Demand forecasting", text: "Know what will sell next so you buy the right stock at the right time." },
  { icon: Boxes, title: "Smart inventory", text: "Low-stock and overstock alerts before they cost you money." },
  { icon: Truck, title: "Procurement & suppliers", text: "Compare suppliers on price and reliability, then raise better purchase orders." },
  { icon: Sparkles, title: "Explainable recommendations", text: "Clear actions with evidence: what to buy, what to discount, what to watch." },
  { icon: ShieldCheck, title: "Secure by design", text: "Role-based access, per-business data isolation and a full audit trail." },
];
const STATS = [["15+", "Business modules"], ["Live", "Data-grounded AI"], ["RBAC", "Owner & manager roles"], ["100%", "Audit-logged actions"]];

export default function Home() {
  const { user, loading, logout } = useAuth();
  const cta = user ? "/dashboard" : "/login";
  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-[#0f172a]/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" aria-label="BizMind BD – home"><Brand /></Link>
          <nav aria-label="Primary" className="flex items-center gap-2 text-sm">
            <a href="#features" className="hidden px-3 py-2 text-slate-400 hover:text-white sm:block">Features</a>
            <a href="#copilot" className="hidden px-3 py-2 text-slate-400 hover:text-white sm:block">AI Copilot</a>
            {!loading && (user ? (<>
              <Link href="/dashboard" className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-950/40 hover:bg-indigo-500">Open dashboard</Link>
              <button onClick={logout} className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800">Sign out</button>
            </>) : (<>
              <Link href="/login" className="px-3 py-2 text-xs font-medium text-slate-300 hover:text-white">Sign in</Link>
              <Link href="/login" className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-950/40 hover:bg-indigo-500">Get started</Link>
            </>))}
          </nav>
        </div>
      </header>

      <section className="bg-[radial-gradient(ellipse_at_top,#1e1b4b_0%,#0b0f19_65%)]">
        <div className="mx-auto max-w-6xl px-4 py-16 text-center sm:px-6 sm:py-24">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-medium text-cyan-300"><Sparkles className="h-3.5 w-3.5" aria-hidden />Intelligent Retail &amp; ERP Operations Suite</span>
          <h1 className="mx-auto mt-5 max-w-3xl text-4xl font-extrabold tracking-tight text-white sm:text-5xl">Understand your business. <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">Decide with data.</span> Stay in control.</h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-slate-400 sm:text-lg">BizMind BD turns your sales, stock, supplier and expense data into clear insights and next-step actions, so you spend less time guessing.</p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href={cta} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950/50 hover:bg-indigo-500">{user ? "Go to your dashboard" : "Start free"}<ArrowRight className="h-4 w-4" aria-hidden /></Link>
            <Link href={user ? "/ai-assistant" : "/login"} className="inline-flex items-center gap-2 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-6 py-3 text-sm font-semibold text-indigo-300 hover:bg-indigo-500/20"><Bot className="h-4 w-4 text-cyan-400" aria-hidden />Try the AI Copilot</Link>
          </div>
          <dl className="mx-auto mt-14 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4">
            {STATS.map(([v, l]) => <div key={l} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><dt className="font-mono text-xl font-bold text-white">{v}</dt><dd className="mt-1 text-xs text-slate-400">{l}</dd></div>)}
          </dl>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-6xl scroll-mt-16 px-4 py-16 sm:px-6">
        <h2 className="text-center text-2xl font-bold text-white">Everything your business needs, in one place</h2>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl shadow-black/20 transition hover:border-indigo-500/50">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/15 text-cyan-400"><Icon className="h-5 w-5" aria-hidden /></span>
              <h3 className="mt-3 font-semibold text-white">{title}</h3>
              <p className="mt-1 text-sm text-slate-400">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="copilot" className="scroll-mt-16 border-y border-slate-800 bg-slate-900/50">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-4 py-14 text-center sm:px-6 md:flex-row md:text-left">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-white">Ask your business anything</h2>
            <p className="mt-2 text-slate-400">“What should I purchase this week?” “Why did profit drop?” The Copilot answers using only your real data, shows its evidence and explains its reasoning.</p>
          </div>
          <Link href={user ? "/ai-assistant" : "/login"} className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-6 py-3 text-sm font-semibold text-white hover:bg-cyan-500">Open AI Copilot<ArrowRight className="h-4 w-4" aria-hidden /></Link>
        </div>
      </section>

      <footer>
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-slate-400 sm:flex-row sm:px-6">
          <Link href="/" aria-label="BizMind BD – home"><Brand /></Link>
          <p>© {new Date().getFullYear()} BizMind BD · Data → Insight → Action</p>
        </div>
      </footer>
    </div>
  );
}
