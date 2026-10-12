"use client";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

/** Loading / error / retry state for a GET request — every page renders through this (MASTER PROMPT §29). */
export function useFetch<T>(path: string | null, params?: Record<string, string | number | undefined | null>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const key = JSON.stringify([path, params]);

  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true); setError(null);
    try { setData(await api<T>(path, { params })); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again."); }
    finally { setLoading(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => { load(); }, [load]);
  return { data, error, loading, reload: load };
}
