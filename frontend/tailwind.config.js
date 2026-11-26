/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#EEF2FF",
          700: "#102F7A",
          800: "#0D296E",
          900: "#0A2463",
          950: "#061742",
        },
        royal: {
          500: "#2563EB",
          600: "#1E40AF",
          700: "#1D4ED8",
        },
        gold: {
          300: "#FDE68A",
          400: "#F5C451",
          500: "#D4AF37",
          600: "#B58E1E",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        display: ["Poppins", "Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
