/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        ink: "#111827",
        muted: "#64748B",
        surface: "#F8FAFC",
        panel: "#FFFFFF",
        border: "#E4E9F0",
        accent: {
          DEFAULT: "#4338CA",
          hover: "#3730A3",
          subtle: "#EEF0FD",
        },
        status: {
          active: "#059669",
          "active-subtle": "#ECFDF5",
          blocked: "#B45309",
          "blocked-subtle": "#FFFBEB",
          conflicted: "#DC2626",
          "conflicted-subtle": "#FEF2F2",
          unknown: "#64748B",
          "unknown-subtle": "#F1F5F9",
        },
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(17 24 39 / 0.04), 0 1px 3px 0 rgb(17 24 39 / 0.06)",
      },
      borderRadius: {
        card: "0.625rem",
      },
    },
  },
  plugins: [],
};
