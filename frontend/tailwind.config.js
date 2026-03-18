export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "#edf3f7",
        card: "#f8fbfd",
        border: "#c8d7e3",
        primary: "#146c94",
        success: "#1f8f6b",
        warning: "#d48a23",
        error: "#c44f4f",
        text: "#10212b",
        muted: "#60717e"
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        serif: ["Georgia", "Times New Roman", "serif"],
        mono: ["JetBrains Mono", "monospace"]
      },
      boxShadow: {
        glow: "0 25px 80px rgba(20, 108, 148, 0.15)",
        paper: "0 20px 60px rgba(20, 47, 61, 0.08)"
      },
      animation: {
        floaty: "floaty 7s ease-in-out infinite",
        "pulse-soft": "pulseSoft 2.4s ease-in-out infinite"
      },
      keyframes: {
        floaty: {
          "0%,100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" }
        },
        pulseSoft: {
          "0%,100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.08)" }
        }
      }
    }
  },
  plugins: []
};
