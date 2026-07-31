import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0f1c1f",
        mist: "#e8eef0",
        teal: {
          DEFAULT: "#0d7c7c",
          soft: "#d4efef",
          deep: "#095858",
        },
        coral: {
          DEFAULT: "#d45d4a",
          soft: "#f8e4df",
          deep: "#a84030",
        },
        sand: "#f3f1ec",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "mesh-pulse": {
          "0%, 100%": { opacity: "0.35", transform: "scale(1)" },
          "50%": { opacity: "0.9", transform: "scale(1.08)" },
        },
        "mesh-draw": {
          "0%": { strokeDashoffset: "120" },
          "100%": { strokeDashoffset: "0" },
        },
        "mesh-float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.35s ease-out",
        "mesh-pulse": "mesh-pulse 3.6s ease-in-out infinite",
        "mesh-draw": "mesh-draw 1.8s ease-out forwards",
        "mesh-float": "mesh-float 7s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
