/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Zinc base — dark foundation
        surface: {
          DEFAULT: '#09090b',  // zinc-950 — app bg
          raised: '#111113',   // cards, panels
          overlay: '#18181b',  // zinc-900 — popovers, hover
          border: '#27272a',   // zinc-800 — borders
          muted: '#3f3f46',    // zinc-700 — disabled, inactive
        },
        // Accent — tematizável via CSS vars (Arc Reactor / Iron Man)
        accent: {
          DEFAULT: 'var(--color-accent)',
          hover: 'var(--color-accent-hover)',
          muted: 'var(--color-accent-muted)',
          faint: 'var(--color-accent-faint)',
          glow: 'var(--color-accent-glow)',
        },
        // Text hierarchy
        text: {
          primary: '#fafafa',    // zinc-50
          secondary: '#a1a1aa',  // zinc-400
          muted: '#71717a',      // zinc-500
          faint: '#52525b',      // zinc-600
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['11px', '16px'],
        xs: ['12px', '16px'],
        sm: ['13px', '20px'],
        base: ['14px', '22px'],
        md: ['15px', '24px'],
        lg: ['16px', '24px'],
        xl: ['18px', '28px'],
        '2xl': ['24px', '32px'],
        '3xl': ['32px', '40px'],
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '6px',
        md: '8px',
        lg: '10px',
        xl: '12px',
      },
      boxShadow: {
        // Borders-only approach — dark UI
        border: '0 0 0 1px rgba(255,255,255,0.06)',
        'border-accent': '0 0 0 1px var(--color-accent)',
        glow: '0 0 0 3px var(--color-accent-glow)',
        // Subtle elevation for floating elements
        float: '0 4px 16px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)',
      },
      animation: {
        'fade-in': 'fadeIn 150ms ease-out',
        'slide-up': 'slideUp 200ms cubic-bezier(0.25, 1, 0.5, 1)',
        'cursor-blink': 'cursorBlink 1s step-end infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        cursorBlink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
    },
  },
  plugins: [],
}
