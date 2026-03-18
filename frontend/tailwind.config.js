export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0f1117",
        card: "#1a1d27",
        border: "#2a2d3a",
        primary: "#08b6f7",
        success: "#22c55e",
        warning: "#f59e0b",
        error: "#ef4444",
        text: "#e2e8f0",
        muted: "#64748b"
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"]
      },
      boxShadow: {
        glow: "0 0 40px rgba(8, 182, 247, 0.24)"
      },
      animation: {
        floaty: "floaty 7s ease-in-out infinite"
      },
      keyframes: {
        floaty: {
          "0%,100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" }
        }
      }
    }
  },
  plugins: []
};
