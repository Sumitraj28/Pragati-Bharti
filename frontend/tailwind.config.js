/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: '#FAF8F5',
          subtle: '#F3EFE8',
          card: '#FFFFFF',
          border: '#E4DDD3',
          borderStrong: '#D1C8BA',
          hover: '#EDE7DC',
          active: '#E3DBD0',
        },
        ink: {
          DEFAULT: '#191817',
          secondary: '#5C5750',
          muted: '#8A847A',
          faint: '#BCB6AC',
        },
        terracotta: {
          50: '#FDF6F3',
          100: '#FAECE6',
          200: '#F5D3C5',
          300: '#EDB49E',
          400: '#DE8667',
          500: '#C85A32',
          600: '#B8451D',
          700: '#993514',
          800: '#7D2A12',
          900: '#672412',
          DEFAULT: '#B8451D',
        },
      },
      fontFamily: {
        display: ['Newsreader', 'Georgia', 'serif'],
        sans: ['Plus Jakarta Sans', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(25, 24, 23, 0.04)',
        'elevated': '0 4px 12px -2px rgba(25, 24, 23, 0.06), 0 2px 4px -1px rgba(25, 24, 23, 0.03)',
      }
    },
  },
  plugins: [],
}
