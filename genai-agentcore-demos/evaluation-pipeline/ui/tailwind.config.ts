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
        status: {
          running: "#3b82f6",
          succeeded: "#22c55e",
          failed: "#ef4444",
          aborted: "#f59e0b",
        },
      },
    },
  },
  plugins: [],
};

export default config;
