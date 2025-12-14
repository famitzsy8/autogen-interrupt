/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          bg: 'var(--color-bg)',
          text: 'var(--color-text)',
          'text-secondary': 'var(--color-text-secondary)',
          'text-muted': 'var(--color-text-muted)',
          'text-faint': 'var(--color-text-faint)',
          border: 'var(--color-border)',
          'border-strong': 'var(--color-border-strong)',
          hover: 'var(--color-hover)',
          surface: 'var(--color-surface)',
          'surface-elevated': 'var(--color-surface-elevated)',
          input: 'var(--color-input)',
          'input-border': 'var(--color-input-border)',
          accent: 'var(--color-accent)',
          'accent-hover': 'var(--color-accent-hover)',
          success: 'var(--color-success)',
          warning: 'var(--color-warning)',
          danger: 'var(--color-danger)',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
}