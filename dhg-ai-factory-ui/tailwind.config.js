/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // DHG Primary Colors
        'dhg-blue': {
          DEFAULT: '#0066CC',
          light: '#3385DB',
          dark: '#004D99',
        },
        'dhg-navy': {
          DEFAULT: '#1A365D',
          light: '#2D4A7C',
          dark: '#0F2540',
        },
        // Agent Colors
        'agent': {
          orchestrator: '#0066CC',
          research: '#059669',
          medical: '#7C3AED',
          curriculum: '#EA580C',
          outcomes: '#DB2777',
          competitor: '#0891B2',
          qa: '#DC2626',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', 'monospace'],
        serif: ['Crimson Text', 'Georgia', 'Times New Roman', 'serif'],
      },
      fontSize: {
        'display': ['48px', { lineHeight: '56px', fontWeight: '700', letterSpacing: '-0.02em' }],
        'h1': ['36px', { lineHeight: '44px', fontWeight: '700', letterSpacing: '-0.01em' }],
        'h2': ['30px', { lineHeight: '38px', fontWeight: '600', letterSpacing: '-0.01em' }],
        'h3': ['24px', { lineHeight: '32px', fontWeight: '600' }],
        'h4': ['20px', { lineHeight: '28px', fontWeight: '600' }],
        'h5': ['16px', { lineHeight: '24px', fontWeight: '600' }],
        'h6': ['14px', { lineHeight: '20px', fontWeight: '600' }],
        'body-lg': ['18px', { lineHeight: '28px' }],
        'body': ['16px', { lineHeight: '24px' }],
        'body-sm': ['14px', { lineHeight: '20px' }],
        'caption': ['12px', { lineHeight: '16px', fontWeight: '500', letterSpacing: '0.01em' }],
        'overline': ['12px', { lineHeight: '16px', fontWeight: '600', letterSpacing: '0.05em' }],
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 4px 12px rgba(0, 0, 0, 0.1)',
        'blue': '0 4px 12px rgba(0, 102, 204, 0.3)',
        'blue-hover': '0 8px 20px rgba(0, 102, 204, 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      borderRadius: {
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
}
