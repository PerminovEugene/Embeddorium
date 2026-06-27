/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        emd: {
          background: "#0e1d2e", // deep navy
          panel: "#eaf4f6", // light aqua background (panel)
          primary: "#50bfc2", // cyan-ish teal for logo/text
          accent: "#4b9aa8", // buttons
          border: "#1c2f40", // borders
          text: "#1b2c3b", // main text
          placeholder: "#6c7a89", // muted text
          buttonText: "#ffffff", // white text for buttons
        },
      },
      fontFamily: {
        display: ["Cinzel", "serif"],
      },
      fontSize: {
        "header-logo": "3rem", // 48px
        "header-title": "2.5rem", // 40px
        "header-sub": "1rem", // 16px
      },
      spacing: {
        "header-x": "2.5rem",
        "header-y": "1.75rem",
      },
    },
  },
  plugins: [],
};
