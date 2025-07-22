/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./*.html",
    "./assets/js/*.js"
  ],
  theme: {
    extend: {
      colors: {
        // Couleurs du thème sombre TeamCity
        'bg': {
          'primary': '#000000',
          'secondary': '#0d1117',
          'tertiary': '#161b22',
          'surface': '#21262d',
          'elevated': '#30363d'
        },
        'text': {
          'primary': '#f0f6fc',
          'secondary': '#8b949e',
          'muted': '#656d76',
          'disabled': '#484f58'
        },
        'accent': {
          'blue': '#58a6ff',
          'green': '#3fb950',
          'purple': '#a5a5ff',
          'orange': '#ffa657',
          'red': '#f85149',
          'yellow': '#f9e71e'
        },
        'border': {
          'subtle': '#30363d',
          'muted': '#21262d'
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif']
      },
      animation: {
        'pulse-slow': 'pulse 2s infinite',
        'spin-slow': 'spin 2s linear infinite'
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms')
  ],
} 