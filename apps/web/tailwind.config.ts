import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        surface: { DEFAULT: "#f8fafc", card: "#ffffff", border: "#e2e8f0" },
        approve: { DEFAULT: "#059669", bg: "#ecfdf5" },
        review: { DEFAULT: "#d97706", bg: "#fffbeb" },
        reject: { DEFAULT: "#dc2626", bg: "#fef2f2" },
        muted: { DEFAULT: "#64748b", foreground: "#475569" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
