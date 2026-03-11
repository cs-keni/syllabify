/**
 * Theme context: light/dark mode. Persists to localStorage.
 * Applies .dark class to document.documentElement when dark mode is active.
 * Easter egg: spam the theme toggle ~10 times to unlock rainbow (Nyan Cat) mode.
 */
import { createContext, useContext, useEffect, useState } from 'react';
import RainbowEasterEggModal from '../components/RainbowEasterEggModal';

const THEME_KEY = 'syllabify-theme';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    if (typeof window === 'undefined') return 'light';
    return localStorage.getItem(THEME_KEY) || 'light';
  });
  const [showRainbowModal, setShowRainbowModal] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('theme-rainbow');
    } else if (theme === 'rainbow') {
      root.classList.remove('dark');
      root.classList.add('theme-rainbow');
    } else {
      root.classList.remove('dark');
      root.classList.remove('theme-rainbow');
    }
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const setTheme = value => {
    if (value === 'rainbow') setThemeState('rainbow');
    else setThemeState(value === 'dark' ? 'dark' : 'light');
  };

  const toggleTheme = () => {
    setThemeState(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  const unlockRainbow = () => {
    setThemeState('rainbow');
    setShowRainbowModal(true);
  };

  const dismissRainbowModal = () => setShowRainbowModal(false);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, unlockRainbow }}>
      {children}
      {showRainbowModal && (
        <RainbowEasterEggModal onClose={dismissRainbowModal} />
      )}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
