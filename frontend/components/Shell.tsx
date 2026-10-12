"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, ReactNode } from "react";
import { AlertTriangle, BarChart3, Bell, Bot, Boxes, Building2, CheckCircle2, ChevronDown, History, LayoutDashboard, LogOut, Menu, Package, Plus, Receipt, Search, Settings, ShoppingCart, Sparkles, TrendingUp, Truck, UserCheck, Users, X } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useFetch } from "@/hooks/useFetch";
import { Loading, cx } from "@/components/ui";
import { Brand } from "@/components/Brand";
import type { Alert, HealthScore, Recommendation, Role } from "@/types";

type Item = { href: string; label: string; icon: any; roles?: Role[]; special?: boolean; badge?: "recs" | "alerts" };
const GROUPS: { group: string; items: Item[] }[] = [
  { group: "Operations", items: [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/sales", label: "Sales & POS", icon: ShoppingCart },
    { href: "/inventory", label: "Inventory", icon: Boxes },
    { href: "/products", label: "Products", icon: Package },
    { href: "/procurement", label: "Procurement", icon: Truck } ] },
  { group: "AI & Intelligence", items: [
    { href: "/forecast", label: "Demand Forecast", icon: TrendingUp },
    { href: "/recommendations", label: "Recommendations", icon: Sparkles, badge: "recs" },
    { href: "/ai-assistant", label: "AI Copilot", icon: Bot, special: true },
    { href: "/alerts", label: "Risk & Alerts", icon: AlertTriangle, badge: "alerts" } ] },
  { group: "Finance & CRM", items: [
    { href: "/analytics", label: "Analytics", icon: BarChart3 },
    { href: "/expenses", label: "Expenses", icon: Receipt },
    { href: "/customers", label: "Customers", icon: Users },
    { href: "/suppliers", label: "Suppliers", icon: Building2 } ] },
  { group: "Management", items: [
    { href: "/employees", label: "Team & RBAC", icon: UserCheck, roles: ["owner"] },
    { href: "/audit-logs", label: "Audit Trail", icon: History, roles: ["owner"] },
    { href: "/settings", label: "Settings", icon: Settings, roles: ["owner"] } ] },
];

export function Shell({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const path = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [q, setQ] = useState("");
  const [focus, setFocus] = useState(false);
  const search = useRef<HTMLInputElement>(null);

  const health = useFetch<HealthScore>(user ? "/api/analytics/health-score" : null);
  const alerts = useFetch<Alert[]>(user ? "/api/alerts" : null, { status: "unread" });
  const recs = useFetch<Recommendation[]>(user ? "/api/ai/recommendations" : null);

  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  useEffect(() => { setOpen(false); setMenu(false); setQ(""); }, [path]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); search.current?.focus(); } };
    window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
  }, []);

  const groups = useMemo(() => GROUPS.map((g) => ({ ...g, items: g.items.filter((i) => !i.roles || (user && i.roles.includes(user.role))) })).filter((g) => g.items.length), [user]);
  if (loading || !user) return <Loading label="Loading your workspace…" />;

  const badges = {
    recs: (recs.data ?? []).filter((r) => r.status === "pending").length,
    alerts: (alerts.data ?? []).filter((a) => a.severity === "critical").length,
  };
  const score = health.data?.overall_score;
  const scoreColor = score == null ? "text-slate-400" : score >= 80 ? "text-emerald-400" : score >= 60 ? "text-amber-400" : "text-rose-400";
  const flat = groups.flatMap((g) => g.items);
  const matches = q.trim() ? flat.filter((i) => i.label.toLowerCase().includes(q.trim().toLowerCase())) : [];
  const isActive = (href: string) => path.startsWith(href);
  const fullBleed = path.startsWith("/ai-assistant");

  const nav = (compact?: boolean) => (
    <div className={compact ? "space-y-6" : "space-y-5 p-3"}>
      {groups.map((g) => (
        <div key={g.group} className="space-y-1">
          <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400">{g.group}</p>
          <div className="space-y-0.5">
            {g.items.map(({ href, label, icon: Icon, special, badge }) => {
              const active = isActive(href); const n = badge ? badges[badge] : 0;
              return (
                <Link key={href} href={href} aria-current={active ? "page" : undefined}
                  className={cx("group flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition",
                    active ? "bg-indigo-600 font-semibold text-white shadow-md shadow-indigo-950" : special ? "text-cyan-300 hover:bg-cyan-950/30 hover:text-cyan-200" : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-100")}>
                  <span className="flex items-center gap-2.5"><Icon className={cx("h-4 w-4 transition", active ? "text-white" : special ? "text-cyan-400" : "text-slate-400 group-hover:text-slate-200")} aria-hidden />{label}</span>
                  {n > 0 && <span className={cx("rounded-full px-1.5 text-[10px] font-bold text-white", badge === "alerts" ? "bg-rose-500" : "bg-indigo-500")}>{n}</span>}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="flex min-h-screen flex-col bg-[#0b0f19] text-slate-100 antialiased">
      <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-slate-800/80 bg-[#0f172a]/80 px-4 backdrop-blur-md sm:px-6">
        <div className="flex min-w-0 items-center gap-2 sm:gap-4">
          <button className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white md:hidden" aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen(!open)}>{open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}</button>
          <Link href="/" aria-label="BizMind BD – go to home page" title="Back to home page"><Brand subtitle={user.full_name ? `${user.full_name}'s workspace` : undefined} /></Link>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <div className="relative hidden lg:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input ref={search} type="text" aria-label="Jump to page" placeholder="Jump to a page… (Ctrl/⌘ K)" value={q} onChange={(e) => setQ(e.target.value)} onFocus={() => setFocus(true)} onBlur={() => setTimeout(() => setFocus(false), 150)}
              onKeyDown={(e) => { if (e.key === "Enter" && matches[0]) router.push(matches[0].href); if (e.key === "Escape") { setQ(""); search.current?.blur(); } }}
              className="w-64 rounded-lg border border-slate-700/60 bg-slate-900/90 py-1.5 pl-9 pr-4 text-xs text-slate-200 placeholder-slate-500 transition focus:border-indigo-500" />
            {focus && q.trim() && (
              <div className="absolute left-0 top-full z-50 mt-2 w-64 rounded-xl border border-slate-800 bg-slate-900 p-1.5 shadow-2xl">
                {matches.length ? matches.map((m) => <Link key={m.href} href={m.href} className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800"><m.icon className="h-3.5 w-3.5 text-slate-400" aria-hidden />{m.label}</Link>) : <p className="px-2.5 py-1.5 text-xs text-slate-400">No matching page</p>}
              </div>
            )}
          </div>

          <Link href="/dashboard" title="Business health score (inventory risk, margin, turnover)" className="hidden items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1.5 text-xs transition hover:border-slate-700 sm:flex">
            <span className="text-[11px] font-medium text-slate-400">Health:</span>
            <span className={cx("font-mono font-bold", scoreColor)}>{score == null ? "—" : `${Math.round(score)}/100`}</span>
            <span className={cx("h-2 w-2 animate-pulse rounded-full", score == null ? "bg-slate-500" : score >= 80 ? "bg-emerald-400" : score >= 60 ? "bg-amber-400" : "bg-rose-400")} />
          </Link>

          <Link href="/alerts" aria-label={`${badges.alerts} critical alerts`} className="relative hidden rounded-lg border border-slate-800 p-2 text-slate-400 transition hover:text-white sm:block">
            <Bell className="h-4 w-4" aria-hidden />{badges.alerts > 0 && <span className="absolute -right-1 -top-1 rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white">{badges.alerts}</span>}
          </Link>

          <Link href="/sales?new=1" className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-md shadow-emerald-900/30 transition hover:bg-emerald-500 active:scale-95"><Plus className="h-3.5 w-3.5" aria-hidden /><span className="hidden sm:inline">New Sale</span><span className="sm:hidden">POS</span></Link>

          <Link href="/ai-assistant" className={cx("hidden items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition sm:flex", fullBleed ? "border-indigo-500 bg-indigo-600 text-white shadow-md shadow-indigo-900/40" : "border-indigo-500/30 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20")}><Bot className="h-3.5 w-3.5 text-cyan-400" aria-hidden /><span className="hidden sm:inline">AI Copilot</span></Link>

          <div className="relative">
            <button onClick={() => setMenu(!menu)} aria-haspopup="menu" aria-expanded={menu} className="flex items-center gap-2 rounded-lg border border-slate-800 p-1.5 transition hover:bg-slate-800/80">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 text-xs font-bold text-white shadow">{user.full_name.charAt(0).toUpperCase()}</span>
              <span className="hidden text-left text-xs leading-tight md:block"><span className="block font-semibold text-slate-200">{user.full_name}</span><span className="block text-[10px] capitalize text-slate-400">{user.role}</span></span>
              <ChevronDown className="hidden h-3.5 w-3.5 text-slate-400 md:block" aria-hidden />
            </button>
            {menu && (
              <div role="menu" className="absolute right-0 z-50 mt-2 w-56 rounded-xl border border-slate-800 bg-slate-900 p-1.5 shadow-2xl">
                <div className="mb-1 border-b border-slate-800/80 px-3 py-2"><p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Signed in as</p><p className="truncate text-xs text-slate-200">{user.email}</p><p className="mt-0.5 flex items-center gap-1 text-[10px] capitalize text-emerald-400"><CheckCircle2 className="h-3 w-3" aria-hidden />{user.role} access</p></div>
                <Link role="menuitem" href="/" className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800"><Sparkles className="h-3.5 w-3.5" aria-hidden />Home page</Link>
                <button role="menuitem" onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-rose-300 hover:bg-slate-800"><LogOut className="h-3.5 w-3.5" aria-hidden />Sign out</button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
        <aside className="hidden w-64 shrink-0 flex-col justify-between overflow-y-auto border-r border-slate-800/80 bg-[#0c1222]/90 md:flex">
          <nav aria-label="Main">{nav()}</nav>
          <div className="border-t border-slate-800/80 bg-slate-950/40 p-3"><div className="flex items-center justify-between text-[11px] text-slate-400"><span className="flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />Live data</span><span className="font-mono text-[10px]">BizMind BD</span></div></div>
        </aside>

        {open && (
          <div className="fixed inset-0 z-50 flex md:hidden">
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
            <aside className="relative z-10 flex w-72 max-w-full flex-col overflow-y-auto border-r border-slate-800 bg-[#0c1222] p-4">
              <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
                <Link href="/" aria-label="BizMind BD – go to home page"><Brand /></Link>
                <button aria-label="Close menu" onClick={() => setOpen(false)} className="rounded p-1 text-slate-400 hover:text-white"><X className="h-5 w-5" /></button>
              </div>
              <nav aria-label="Main mobile">{nav(true)}</nav>
            </aside>
          </div>
        )}

        {fullBleed
          ? <main className="flex h-[calc(100vh-4rem)] min-h-0 min-w-0 flex-1 flex-col bg-gradient-to-b from-[#0b0f19] to-[#080b12]">{children}</main>
          : <main className="min-w-0 flex-1 overflow-y-auto bg-gradient-to-b from-[#0b0f19] to-[#080b12] p-4 sm:p-6 lg:p-8"><div className="mx-auto w-full max-w-7xl">{children}</div></main>}
      </div>
    </div>
  );
}
