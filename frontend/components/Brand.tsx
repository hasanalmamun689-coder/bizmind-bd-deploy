import { Sparkles } from "lucide-react";

/** BizMind BD wordmark (matches the draft header). Wrap in <Link href="/"> wherever it should return to the home page. */
export function Brand({ size = "md", subtitle }: { size?: "md" | "lg"; subtitle?: string }) {
  const lg = size === "lg";
  return (
    <span className="group inline-flex select-none items-center gap-3">
      <span className={`rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-500 to-cyan-400 p-[1px] shadow-lg shadow-indigo-500/20 ${lg ? "h-11 w-11" : "h-9 w-9"}`}>
        <span className="flex h-full w-full items-center justify-center rounded-[11px] bg-slate-950">
          <Sparkles className={`text-cyan-400 transition-transform duration-300 group-hover:rotate-12 ${lg ? "h-5 w-5" : "h-4 w-4"}`} aria-hidden />
        </span>
      </span>
      <span className="text-left">
        <span className="flex items-center gap-2">
          <span className={`bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text font-extrabold tracking-tight text-transparent ${lg ? "text-xl" : "text-base"}`}>BIZMIND</span>
          <span className="rounded border border-emerald-500/30 bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">BD</span>
        </span>
        {subtitle && <span className="hidden max-w-[200px] sm:block truncate text-[11px] text-slate-400">{subtitle}</span>}
      </span>
    </span>
  );
}
