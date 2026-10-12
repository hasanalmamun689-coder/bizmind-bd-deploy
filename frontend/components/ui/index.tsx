"use client";
import { createContext, useCallback, useContext, useEffect, useState, ReactNode, ButtonHTMLAttributes, InputHTMLAttributes, SelectHTMLAttributes } from "react";
import { AlertTriangle, CheckCircle2, Inbox, Loader2, X } from "lucide-react";

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

/* ---------- Button ---------- */
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost"; size?: "sm" | "md"; busy?: boolean };
export function Button({ variant = "primary", size = "md", busy, className, children, disabled, ...p }: BtnProps) {
  const v = {
    primary: "bg-indigo-600 text-white shadow-md shadow-indigo-950/40 hover:bg-indigo-500 active:scale-95",
    secondary: "bg-slate-900 text-slate-200 border border-slate-700 hover:border-indigo-500 hover:text-white",
    danger: "bg-rose-600 text-white hover:bg-rose-500",
    ghost: "text-slate-400 hover:bg-slate-800 hover:text-white",
  }[variant];
  return (
    <button {...p} disabled={disabled || busy}
      className={cx("inline-flex items-center justify-center gap-2 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed", size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3.5 py-2 text-sm", v, className)}>
      {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}{children}
    </button>
  );
}

/* ---------- Form fields ---------- */
export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-300">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </label>
  );
}
const field = "w-full rounded-lg border border-slate-700/70 bg-slate-900/90 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 transition focus:border-indigo-500";
export const Input = (p: InputHTMLAttributes<HTMLInputElement>) => <input {...p} className={cx(field, p.className)} />;
export const Select = (p: SelectHTMLAttributes<HTMLSelectElement>) => <select {...p} className={cx(field, p.className)} />;

/* ---------- Card / KPI ---------- */
export const Card = ({ title, action, children, className }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) => (
  <section className={cx("min-w-0 rounded-2xl border border-slate-800 bg-slate-900/70 shadow-xl shadow-black/20", className)}>
    {(title || action) && (
      <header className="flex items-center justify-between gap-2 border-b px-4 py-3">
        <h2 className="text-sm font-semibold text-white">{title}</h2>{action}
      </header>
    )}
    <div className="p-4">{children}</div>
  </section>
);

export function KpiCard({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "good" | "bad" | "warn" }) {
  const t = tone === "bad" ? "text-rose-400" : tone === "good" ? "text-emerald-400" : tone === "warn" ? "text-amber-400" : "text-white";
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-xl shadow-black/20">
      <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
      <p className={cx("mt-1 font-mono text-2xl font-semibold", t)}>{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

/* ---------- Badge ---------- */
const tones: Record<string, string> = {
  healthy: "bg-emerald-500/15 text-emerald-300", low_stock: "bg-amber-500/15 text-amber-300", critical: "bg-rose-500/15 text-rose-300",
  out_of_stock: "bg-rose-500/15 text-rose-300", overstock: "bg-violet-500/15 text-violet-300",
  info: "bg-sky-500/15 text-sky-300", warning: "bg-amber-500/15 text-amber-300",
  low: "bg-emerald-500/15 text-emerald-300", moderate: "bg-amber-500/15 text-amber-300", high: "bg-orange-500/15 text-orange-300",
  draft: "bg-slate-800 text-slate-300", pending_approval: "bg-amber-500/15 text-amber-300", approved: "bg-emerald-500/15 text-emerald-300",
  ordered: "bg-sky-500/15 text-sky-300", delivered: "bg-indigo-500/15 text-indigo-300", completed: "bg-emerald-500/15 text-emerald-300", cancelled: "bg-rose-500/15 text-rose-300",
  pending: "bg-amber-500/15 text-amber-300", rejected: "bg-rose-500/15 text-rose-300",
  unread: "bg-indigo-500/15 text-indigo-300", read: "bg-slate-800 text-slate-400", resolved: "bg-emerald-500/15 text-emerald-300", dismissed: "bg-slate-800 text-slate-500",
  new: "bg-sky-500/15 text-sky-300", regular: "bg-emerald-500/15 text-emerald-300", "high-value": "bg-violet-500/15 text-violet-300", inactive: "bg-slate-800 text-slate-400",
};
export const Badge = ({ value: raw, label }: { value?: string | null; label?: string }) => {
  const value = raw ?? "unknown";
  return (
  <span className={cx("inline-block rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap", tones[value] ?? "bg-slate-800 text-slate-300")}>
    {label ?? value.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())}
  </span>
  );
};

/* ---------- Page states (loading / empty / error+retry) ---------- */
export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div role="status" className="flex items-center justify-center gap-2 py-16 text-sm text-slate-400"><Loader2 className="h-5 w-5 animate-spin" aria-hidden />{label}</div>;
}
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-10 text-center">
      <AlertTriangle className="h-6 w-6 text-rose-400" aria-hidden />
      <p className="max-w-md text-sm text-rose-200">{message}</p>
      {onRetry && <Button variant="secondary" size="sm" onClick={onRetry}>Try again</Button>}
    </div>
  );
}
export function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center text-slate-400">
      <Inbox className="h-7 w-7" aria-hidden /><p className="max-w-sm text-sm">{message}</p>{action}
    </div>
  );
}
/** Renders the right state for a useFetch result. */
export function Async<T>({ state, empty, children }: { state: { data: T | null; error: string | null; loading: boolean; reload: () => void }; empty?: { when: (d: T) => boolean; message: string; action?: ReactNode }; children: (d: T) => ReactNode }) {
  if (state.loading && !state.data) return <Loading />;
  if (state.error) return <ErrorState message={state.error} onRetry={state.reload} />;
  if (state.data == null) return <Loading />;
  if (empty?.when(state.data)) return <EmptyState message={empty.message} action={empty.action} />;
  return <>{children(state.data)}</>;
}

/* ---------- Table ---------- */
export interface Col<T> { header: string; cell: (row: T) => ReactNode; className?: string }
export function Table<T>({ cols, rows, rowKey }: { cols: Col<T>[]; rows: T[]; rowKey: (r: T) => string }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/70 shadow-xl shadow-black/20">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-950/60 text-left text-[11px] font-bold uppercase tracking-wider text-slate-400">
          <tr>{cols.map((c) => <th key={c.header} scope="col" className={cx("px-4 py-2.5 font-medium", c.className)}>{c.header}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-800/80">
          {rows.map((r) => (
            <tr key={rowKey(r)} className="hover:bg-slate-800/40">
              {cols.map((c) => <td key={c.header} className={cx("px-4 py-2.5 align-middle", c.className)}>{c.cell(r)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- Modal ---------- */
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 backdrop-blur-sm sm:items-center sm:p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-2xl border border-slate-800 bg-slate-900 shadow-2xl sm:rounded-2xl">
        <div className="flex items-center justify-between border-b px-5 py-3">
          <h2 className="font-semibold text-white">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

/* ---------- Toasts ---------- */
interface Toast { id: number; kind: "success" | "error"; text: string }
const ToastCtx = createContext<(kind: Toast["kind"], text: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s, { id, kind, text }]);
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), 4500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 right-4 z-[60] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
        {items.map((t) => (
          <div key={t.id} className={cx("flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm shadow-lg", t.kind === "success" ? "border-emerald-500/30 bg-emerald-950 text-emerald-200" : "border-rose-500/30 bg-rose-950 text-rose-200")}>
            {t.kind === "success" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />}{t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div><h1 className="text-xl font-bold tracking-tight text-white">{title}</h1>{subtitle && <p className="mt-0.5 text-sm text-slate-400">{subtitle}</p>}</div>
      {action}
    </div>
  );
}
