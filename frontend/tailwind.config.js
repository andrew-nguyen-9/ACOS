import tailwindAnimate from "tailwindcss-animate";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        accent: "#4c8dff",
        verified: "#30D158",
        strong: "#5AC8FA",
        weak: "#FF9F0A",
      },
      height: {
        "10.5": "2.625rem",
      },
    },
  },
  plugins: [tailwindAnimate],
};
