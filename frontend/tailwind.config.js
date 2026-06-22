import plugin from "tailwindcss/plugin";
import tailwindAnimate from "tailwindcss-animate";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // System SF Pro on macOS, Inter fallback — driven by tokens.css.
        sans: ["var(--font-sans)"],
        display: ["var(--font-display)"],
      },
      colors: {
        // sRGB channels → opacity modifiers (bg-accent/10) work; see tokens.css.
        accent: "rgb(var(--accent-rgb) / <alpha-value>)",
        verified: "rgb(var(--verified-rgb) / <alpha-value>)",
        strong: "rgb(var(--strong-rgb) / <alpha-value>)",
        weak: "rgb(var(--weak-rgb) / <alpha-value>)",
      },
      // Tailwind's default spacing already is the 4px baseline grid; this is the
      // one half-step the shell needs.
      height: {
        "10.5": "2.625rem",
      },
      transitionTimingFunction: {
        standard: "var(--ease-standard)",
        "out-expo": "var(--ease-out)",
      },
      transitionDuration: {
        fast: "var(--duration-fast)",
        base: "var(--duration-base)",
        slow: "var(--duration-slow)",
      },
      boxShadow: {
        card: "var(--elevation-card)",
        panel: "var(--elevation-panel)",
      },
    },
  },
  plugins: [
    tailwindAnimate,
    // CSS containment (PERF-RP-002) — not a default Tailwind utility in v3.
    plugin(({ addUtilities }) => {
      addUtilities({
        ".contain-paint": { contain: "layout paint" },
        ".contain-strict": { contain: "strict" },
      });
    }),
  ],
};
