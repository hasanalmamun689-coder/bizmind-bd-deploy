"use client";
import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, tokenStore } from "@/lib/api";
import type { TokenResponse, User } from "@/types";

interface AuthCtx { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; register: (b: Record<string, string>) => Promise<void>; logout: () => void }
const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!tokenStore.get()) { setLoading(false); return; }
    api<User>("/api/auth/me").then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const finish = (r: TokenResponse) => { tokenStore.set(r.access_token); setUser(r.user); router.push("/dashboard"); };
  const login = useCallback(async (email: string, password: string) => finish(await api<TokenResponse>("/api/auth/login", { method: "POST", body: { email, password } })), []); // eslint-disable-line
  const register = useCallback(async (b: Record<string, string>) => finish(await api<TokenResponse>("/api/auth/register", { method: "POST", body: b })), []); // eslint-disable-line
  const logout = useCallback(() => { tokenStore.clear(); setUser(null); router.push("/login"); }, [router]);

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}
