/**
 * Accent color context. Persists to localStorage.
 * Applies --color-accent, --color-accent-hover, --color-accent-muted to document.
 */
import { createContext, useContext, useState, useEffect } from 'react';

const ACCENT_KEY = 'syllabify-accent';

const PALETTES = {
  green: {
    accent: '#0f8a4c',
    accentHover: '#094728',
    accentMuted: '#dcfce7',
  },
  blue: {
    accent: '#2563eb',
    accentHover: '#1d4ed8',
    accentMuted: '#dbeafe',
  },
  purple: {
    accent: '#7c3aed',
    accentHover: '#5b21b6',
    accentMuted: '#ede9fe',
  },
  indigo: {
    accent: '#4f46e5',
    accentHover: '#3730a3',
    accentMuted: '#e0e7ff',
  },
};

const AccentContext = createContext(null);

export function AccentProvider({ children }) {
  const [accent, setAccentState] = useState(() => {
    if (typeof window === 'undefined') return 'green';
    return localStorage.getItem(ACCENT_KEY) || 'green';
  });

  useEffect(() => {
    const p = PALETTES[accent] || PALETTES.green;
    const root = document.documentElement;
    root.style.setProperty('--color-accent', p.accent);
    root.style.setProperty('--color-accent-hover', p.accentHover);
    root.style.setProperty('--color-accent-muted', p.accentMuted);
    try {
      localStorage.setItem(ACCENT_KEY, accent);
    } catch (_) {}
  }, [accent]);

  const setAccent = value => {
    setAccentState(PALETTES[value] ? value : 'green');
  };

  return (
    <AccentContext.Provider value={{ accent, setAccent, palettes: Object.keys(PALETTES) }}>
      {children}
    </AccentContext.Provider>
  );
}

export function useAccent() {
  const ctx = useContext(AccentContext);
  return ctx || { accent: 'green', setAccent: () => {}, palettes: ['green'] };
}
