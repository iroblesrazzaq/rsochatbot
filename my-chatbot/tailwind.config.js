/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        // Here we add our custom colors while preserving all default Tailwind colors
        colors: {
          maroon: '#800000',
          // You can also add variations if needed
          'maroon-light': '#a05555',
          'maroon-dark': '#600000',
        }
      },
    },
    plugins: [],
  }