/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAF9F6",
        ink: {
          DEFAULT: "#12433F",
          light: "#1D5A54",
          dark: "#0B2E2B",
        },
        clay: {
          DEFAULT: "#C97A2B",
          light: "#E0954A",
        },
      },
      fontFamily: {
        display: ['"Fraunces"', "serif"],
        sans: ['"IBM Plex Sans"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "monospace"],
      },
    },
  },
  plugins: [],
};
