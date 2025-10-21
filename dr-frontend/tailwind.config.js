/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        // GitHub dark theme colors
        dark: {
          bg: '#0d1117',
          text: '#c9d1d9',
          border: '#30363d',
          hover: '#161b22',
          accent: '#58a6ff',
        },
        // Agent colors (40% opacity versions)
        agent: {
          jara: 'rgba(239, 68, 68, 0.4)',      // red
          kast: 'rgba(59, 130, 246, 0.4)',     // blue
          neural: 'rgba(168, 85, 247, 0.4)',   // purple
          modLeft: 'rgba(125, 211, 252, 0.4)', // light blue
          modRight: 'rgba(251, 146, 60, 0.4)', // orange
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
