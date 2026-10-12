export const taka = (n: number | null | undefined) =>
  n == null ? "—" : "৳" + Math.round(n).toLocaleString("en-IN");
export const num = (n: number) => n.toLocaleString("en-IN");
export const dateShort = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";
export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
export const titleCase = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
