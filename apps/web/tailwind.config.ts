import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        emerald: {
          DEFAULT: "#10b981",
          bright: "#34d399",
        },
        electric: {
          DEFAULT: "#2563eb",
          bright: "#3b82f6",
        },
        neon: {
          emerald: "#00ff88",
          cyan: "#00f0ff",
          purple: "#a855f7",
          gold: "#fbbf24",
        },
        obsidian: "#010409",
        graphite: {
          950: "#0b0e13",
          900: "#11151c",
          850: "#151a22",
          800: "#1a2029",
          700: "#232a36",
          600: "#2e3647",
          500: "#454f63",
          400: "#6b7688",
          300: "#9aa3b2",
          200: "#c3c9d4",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -8px rgba(0,0,0,0.5)",
        glow: "0 0 0 1px rgba(16,185,129,0.25), 0 8px 24px -8px rgba(16,185,129,0.25)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-468px 0" },
          "100%": { backgroundPosition: "468px 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
