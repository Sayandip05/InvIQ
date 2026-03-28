/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#2563eb",
        secondary: "#475569",
        success: "#22c55e",
        warning: "#f59e0b",
        danger: "#ef4444",
      }
    },
  },
  plugins: [],
}
