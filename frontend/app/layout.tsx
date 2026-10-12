import "./globals.css";
import type { Metadata, Viewport } from "next";
import { AuthProvider } from "@/hooks/useAuth";
import { ToastProvider } from "@/components/ui";
import { PwaRegistration } from "@/components/PwaRegistration";

export const metadata: Metadata = {
  title: "BizMind BD — Intelligent Retail & ERP Operations Suite",
  description: "BizMind BD: inventory, sales, demand forecasting, procurement, risk alerts and an AI copilot grounded in your real business data.",
  applicationName: "BizMind BD",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg", apple: "/icon.svg" },
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "BizMind BD" },
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#0b0f19" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
      </head>
      <body><PwaRegistration /><AuthProvider><ToastProvider>{children}</ToastProvider></AuthProvider></body>
    </html>
  );
}
