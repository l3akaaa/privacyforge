/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pii: "#dc2626",
        sensitive: "#d97706",
        quasi: "#2563eb",
      },
    },
  },
  plugins: [],
};
