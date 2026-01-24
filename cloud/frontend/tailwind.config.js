/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ApexAurum brand colors
        gold: {
          DEFAULT: '#D4AF37',
          dim: '#A08030',
          bright: '#FFD700',
        },
        apex: {
          dark: '#0D0D0D',
          darker: '#050505',
          card: '#1a1a1a',
          border: '#333',
        },
        // Agent colors
        azoth: '#D4AF37',
        elysian: '#9B59B6',
        vajra: '#E74C3C',
        kether: '#3498DB',
        claude: '#6B8AFD',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        serif: ['Cinzel', 'serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
