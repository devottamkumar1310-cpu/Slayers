/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#090d16',
        surface: '#111827',
        surfaceBorder: '#1f293d',
        accent: {
          DEFAULT: '#3b82f6',
          hover: '#2563eb',
        },
        emeraldGlow: '#10b981',
        warningGold: '#f59e0b',
      },
    },
  },
  plugins: [],
}
