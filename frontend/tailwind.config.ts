import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Plus Jakarta Sans", "system-ui", "sans-serif"], mono: ["JetBrains Mono", "ui-monospace", "monospace"] },
      colors: {
        // BizMind BD draft palette: indigo primary, cyan accent, emerald for positive/POS actions
        brand: { 50: "rgba(99,102,241,0.12)", 100: "rgba(99,102,241,0.2)", 500: "#6366f1", 600: "#4f46e5", 700: "#818cf8" },
      },
    },
  },
  plugins: [],
};
export default config;
