import type { Config } from "tailwindcss";

const v = (name: string) => `var(--${name})`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    // UI_DESIGN §3 breakpoints: 760px (sidebar → top nav) and 1000px (two columns stack).
    screens: { sm: "640px", md: "760px", lg: "1000px", xl: "1280px" },
    extend: {
      colors: {
        bg: v("bg"),
        surface: { DEFAULT: v("surface"), 2: v("surface-2") },
        border: { DEFAULT: v("border"), strong: v("border-strong") },
        text: { DEFAULT: v("text"), 2: v("text-2"), 3: v("text-3") },
        accent: { DEFAULT: v("accent"), soft: v("accent-soft"), text: v("accent-text") },
        "on-accent": v("on-accent"),
        pass: { DEFAULT: v("pass"), soft: v("pass-soft") },
        review: { DEFAULT: v("review"), soft: v("review-soft") },
        fail: { DEFAULT: v("fail"), soft: v("fail-soft") },
        "on-status": v("on-status"),
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: { card: "10px", ctl: "6px" },
      boxShadow: { card: v("shadow") },
      fontSize: { xs: ["12px", "1.4"], sm: ["13px", "1.45"], base: ["14px", "1.5"] },
    },
  },
  plugins: [],
} satisfies Config;
