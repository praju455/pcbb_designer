export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        background: "#f3ede2",
        card: "#fbf7f0",
        border: "#d7c8b4",
        primary: "#8b5e3c",
        success: "#456b53",
        warning: "#a9752a",
        error: "#9b4338",
        text: "#1f1a17",
        muted: "#6f6459"
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        serif: ["Georgia", "Times New Roman", "serif"],
        mono: ["JetBrains Mono", "monospace"]
      },
      boxShadow: {
        glow: "0 25px 80px rgba(74, 54, 35, 0.14)",
        paper: "0 20px 60px rgba(56, 39, 27, 0.08)"
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
