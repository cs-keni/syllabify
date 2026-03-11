/**
 * Light/dark theme toggle button.
 * Easter egg: click ~10 times quickly (within 2s) to unlock rainbow (Nyan Cat) mode.
 * In rainbow mode, click once to return to light/dark.
 */
import { useRef } from 'react';
import { useTheme } from '../contexts/ThemeContext';

const EASTER_EGG_CLICKS = 10;
const EASTER_EGG_WINDOW_MS = 2000;

export default function ThemeToggle() {
  const { theme, toggleTheme, unlockRainbow } = useTheme();
  const clickCountRef = useRef(0);
  const lastClickRef = useRef(0);

  const handleClick = () => {
    const now = Date.now();
    if (now - lastClickRef.current > EASTER_EGG_WINDOW_MS) {
      clickCountRef.current = 0;
    }
    lastClickRef.current = now;
    clickCountRef.current += 1;

    if (theme === 'rainbow') {
      toggleTheme();
      return;
    }
    if (clickCountRef.current >= EASTER_EGG_CLICKS) {
      clickCountRef.current = 0;
      unlockRainbow();
      return;
    }
    toggleTheme();
  };

  const title =
    theme === 'rainbow'
      ? 'Click to return to light/dark mode'
      : theme === 'dark'
        ? 'Switch to light mode'
        : 'Switch to dark mode';

  return (
    <button
      type="button"
      onClick={handleClick}
      className="rounded-button p-2 text-ink-muted hover:bg-surface-muted hover:text-ink active:scale-95 transition-all duration-200"
      title={title}
      aria-label={title}
    >
      {theme === 'rainbow' || theme === 'dark' ? (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="w-5 h-5"
        >
          <path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z" />
        </svg>
      ) : (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="w-5 h-5"
        >
          <path
            fillRule="evenodd"
            d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z"
            clipRule="evenodd"
          />
        </svg>
      )}
    </button>
  );
}
