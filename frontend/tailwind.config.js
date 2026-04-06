/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Bloomberg/Cyberpunk terminal palette
        terminal: {
          bg: "#0a0e17",
          surface: "#111827",
          panel: "#1a1f2e",
          border: "#1e293b",
          "border-bright": "#334155",
          text: "#e2e8f0",
          muted: "#64748b",
          accent: "#f97316", // Orange - MapleStory vibes
          green: "#22c55e",
          red: "#ef4444",
          yellow: "#eab308",
          cyan: "#06b6d4",
          purple: "#a855f7",
          blue: "#3b82f6",
        },
      },
      fontFamily: {
        mono: [
          "JetBrains Mono",
          "Fira Code",
          "SF Mono",
          "Consolas",
          "monospace",
        ],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow": "glow 2s ease-in-out infinite alternate",
        "scan": "scan 4s linear infinite",
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 5px rgba(249, 115, 22, 0.3)" },
          "100%": { boxShadow: "0 0 20px rgba(249, 115, 22, 0.6)" },
        },
        scan: {
          "0%": { backgroundPosition: "0% 0%" },
          "100%": { backgroundPosition: "0% 100%" },
        },
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(rgba(249, 115, 22, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(249, 115, 22, 0.03) 1px, transparent 1px)",
        "scanline":
          "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)",
      },
      backgroundSize: {
        "grid": "20px 20px",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
