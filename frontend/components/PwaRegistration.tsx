"use client";

import { useEffect } from "react";

/** Registers the offline shell only in browsers that support service workers. */
export function PwaRegistration() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => { void navigator.serviceWorker.register("/sw.js"); }, { once: true });
    }
  }, []);
  return null;
}
