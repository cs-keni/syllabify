/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        /* Theme-ready: CSS vars switch with .dark class */
        surface: {
          DEFAULT: 'var(--color-surface)',
          elevated: 'var(--color-surface-elevated)',
          muted: 'var(--color-surface-muted)',
        },
        ink: {
          DEFAULT: 'var(--color-ink)',
          muted: 'var(--color-ink-muted)',
          subtle: 'var(--color-ink-subtle)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          hover: 'var(--color-accent-hover)',
          muted: 'var(--color-accent-muted)',
        },
        border: {
          DEFAULT: 'var(--color-border)',
          subtle: 'var(--color-border-subtle)',
        },
        /* Muted course blocks (weekly view) */
        course: {
          1: '#dbeafe',
          2: '#dcfce7',
          3: '#fef3c7',
          4: '#fce7f3',
          5: '#e0e7ff',
        },
        conflict: '#fef2f2',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '12px',
        button: '8px',
        input: '8px',
      },
      boxShadow: {
        card: '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)',
        dropdown: '0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        barGrow: {
          '0%': { transform: 'scaleY(0)' },
          '100%': { transform: 'scaleY(1)' },
        },
      },
      animation: {
        /* both = backwards (start hidden) + forwards (end visible) */
        'fade-in': 'fadeIn 600ms ease-out both',
        'fade-in-up': 'fadeInUp 800ms ease-out both',
        'scale-in': 'scaleIn 500ms ease-out both',
        'slide-down': 'slideDown 400ms ease-out both',
        'pulse-soft': 'pulseSoft 3s ease-in-out infinite',
        'bar-grow': 'barGrow 800ms ease-out both',
      },
      transitionDuration: {
        150: '300ms',
        200: '400ms',
        250: '500ms',
        300: '600ms',
        350: '700ms',
        400: '800ms',
      },
      animationDelay: {
        50: '100ms',
        80: '160ms',
        100: '200ms',
        120: '240ms',
        150: '300ms',
        200: '400ms',
        250: '500ms',
        300: '600ms',
      },
    },
  },
  plugins: [],
};
