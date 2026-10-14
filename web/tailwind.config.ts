import type { Config } from "tailwindcss";

// Tokens in globals.css are bare HSL triplets ("200 90% 55%"), so each colour
// wraps them in hsl() to keep Tailwind's opacity modifiers (bg-danger/10) working.
const hsl = (token: string) => `hsl(var(--rora-${token}) / <alpha-value>)`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: hsl("bg"),
        panel: hsl("surface"),
        edge: hsl("border"),
        ink: hsl("text"),
        muted: hsl("text-muted"),
        accent: hsl("accent"),
        "accent-soft": hsl("accent-soft"),
        danger: hsl("danger"),
        success: hsl("success"),
        warn: hsl("warn"),
        code: hsl("code-bg"),
      },
      fontFamily: {
        sans: ["var(--rora-font-body)", "system-ui", "sans-serif"],
        mono: ["var(--rora-font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        panel: "var(--rora-radius)",
      },
      boxShadow: {
        panel: "var(--rora-shadow)",
        pop: "var(--rora-shadow-pop)",
      },
    },
  },
  plugins: [],
};
export default config;
