/**
 * Easter egg modal: confetti + message when user unlocks rainbow theme.
 * Cat GIF bounces around corners then center before user can close.
 * Only OK/X close the modal – no backdrop click, so spamming won't accidentally dismiss.
 */
import { useEffect, useState } from 'react';
import confetti from 'canvas-confetti';

const RAINBOW_COLORS = [
  '#ff0000',
  '#ff7f00',
  '#ffff00',
  '#00ff00',
  '#0000ff',
  '#4b0082',
  '#8f00ff',
];

const GIF_POSITIONS = [
  {
    left: '1.5rem',
    bottom: '1.5rem',
    right: 'auto',
    top: 'auto',
    transform: 'scale(2)',
    transformOrigin: 'bottom left',
  },
  {
    left: 'auto',
    bottom: 'auto',
    right: '1.5rem',
    top: '1.5rem',
    transform: 'scale(2)',
    transformOrigin: 'top right',
  },
  {
    left: 'auto',
    bottom: '1.5rem',
    right: '1.5rem',
    top: 'auto',
    transform: 'scale(2)',
    transformOrigin: 'bottom right',
  },
  {
    left: '1.5rem',
    bottom: 'auto',
    right: 'auto',
    top: '1.5rem',
    transform: 'scale(2)',
    transformOrigin: 'top left',
  },
  {
    left: '50%',
    bottom: 'auto',
    right: 'auto',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    width: '100vw',
    height: '100vh',
    maxWidth: '100vw',
    maxHeight: '100vh',
    objectFit: 'contain',
  },
];

export default function RainbowEasterEggModal({ onClose }) {
  const [gifPosition, setGifPosition] = useState(-1);
  const [canClose, setCanClose] = useState(false);

  useEffect(() => {
    const delays = [0, 250, 500, 750, 1000];
    const timeouts = delays.map((d, i) =>
      setTimeout(() => setGifPosition(i), d)
    );
    const doneTimeout = setTimeout(() => {
      setGifPosition(-1);
      setCanClose(true);
    }, 1500);
    return () => {
      timeouts.forEach(clearTimeout);
      clearTimeout(doneTimeout);
    };
  }, []);

  useEffect(() => {
    const duration = 3 * 1000;
    const end = Date.now() + duration;

    const frame = () => {
      confetti({
        particleCount: 4,
        angle: 60,
        spread: 55,
        origin: { x: 0 },
        colors: RAINBOW_COLORS,
      });
      confetti({
        particleCount: 4,
        angle: 120,
        spread: 55,
        origin: { x: 1 },
        colors: RAINBOW_COLORS,
      });
      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    };
    frame();

    const t = setTimeout(() => {
      confetti({
        particleCount: 120,
        spread: 80,
        origin: { y: 0.6 },
        colors: RAINBOW_COLORS,
      });
    }, 500);

    return () => clearTimeout(t);
  }, []);

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 pointer-events-none">
      <div
        className="absolute inset-0 bg-black/50 pointer-events-auto"
        aria-hidden
      />
      {/* Cat GIF bounces: bottom-left → top-right → bottom-right → top-left → center (2x) */}
      {gifPosition >= 0 && (
        <img
          src="/cat-tongue-shake.gif"
          alt=""
          className={`absolute z-20 object-contain pointer-events-none ${
            gifPosition === 4
              ? 'w-screen h-screen'
              : 'w-24 h-24 transition-all duration-200 ease-out'
          }`}
          style={GIF_POSITIONS[gifPosition]}
        />
      )}
      <div
        className="relative z-10 max-w-md rounded-2xl border-2 border-amber-400 bg-surface-elevated p-6 shadow-2xl animate-scale-in pointer-events-auto"
        role="dialog"
        aria-labelledby="easter-egg-title"
        aria-modal="true"
      >
        <button
          type="button"
          onClick={canClose ? onClose : undefined}
          disabled={!canClose}
          className={`absolute top-3 right-3 rounded-button p-1.5 transition-colors ${
            canClose
              ? 'text-ink-muted hover:bg-surface-muted hover:text-ink cursor-pointer'
              : 'text-ink-subtle cursor-not-allowed opacity-50'
          }`}
          aria-label="Close"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
        <h2 id="easter-egg-title" className="text-xl font-bold text-ink pr-8">
          Are you trying to have a stroke?
        </h2>
        <p className="mt-2 text-ink-muted">Why would you spam that button?</p>
        <p className="mt-4 text-sm text-ink-subtle">
          (You unlocked the rainbow theme. Enjoy.)
        </p>
        <button
          type="button"
          onClick={canClose ? onClose : undefined}
          disabled={!canClose}
          className={`mt-6 w-full rounded-button px-4 py-2.5 font-medium transition-colors ${
            canClose
              ? 'bg-accent text-white hover:bg-accent-hover cursor-pointer'
              : 'bg-surface-muted text-ink-muted cursor-not-allowed'
          }`}
        >
          OK
        </button>
      </div>
    </div>
  );
}
