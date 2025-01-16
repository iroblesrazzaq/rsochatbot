/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        maroon: '#800000',
        'maroon-light': '#a05555',
        'maroon-dark': '#600000',
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}