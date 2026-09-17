/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#0F172A",
        card: "#1E293B",
        line: "#334155",
        muted: "#CBD5E1",
        accent: "#6366F1",
        ai: "#8B5CF6",
        ok: "#10B981",
        warn: "#F59E0B",
        danger: "#F43F5E",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
