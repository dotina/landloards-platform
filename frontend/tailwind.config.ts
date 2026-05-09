import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paid: { 500: "#16a34a" },
        due: { 500: "#f59e0b" },
        overdue: { 500: "#dc2626" },
      },
    },
  },
  plugins: [],
};
export default config;
