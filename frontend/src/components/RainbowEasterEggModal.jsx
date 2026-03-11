/**
 * Easter egg modal: confetti + message when user unlocks rainbow theme.
 * Only OK/X close the modal – no backdrop click, so spamming won't accidentally dismiss.
 */
import { useEffect } from 'react';
import confetti from 'canvas-confetti';

const RAINBOW_COLORS = ['#ff0000', '#ff7f00', '#ffff00', '#00ff00', '#0000ff', '#4b0082', '#8f00ff'];

export default function RainbowEasterEggModal({ onClose }) {
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
      <div className="absolute inset-0 bg-black/50 pointer-events-auto" aria-hidden />
      <div
        className="relative z-10 max-w-md rounded-2xl border-2 border-amber-400 bg-surface-elevated p-6 shadow-2xl animate-scale-in pointer-events-auto"
        role="dialog"
        aria-labelledby="easter-egg-title"
        aria-modal="true"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 rounded-button p-1.5 text-ink-muted hover:bg-surface-muted hover:text-ink transition-colors"
          aria-label="Close"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <h2 id="easter-egg-title" className="text-xl font-bold text-ink pr-8">
          Are you trying to have a stroke?
        </h2>
        <p className="mt-2 text-ink-muted">
          Why would you spam that button?
        </p>
        <p className="mt-4 text-sm text-ink-subtle">
          (You unlocked the rainbow theme. Enjoy.)
        </p>
        <button
          type="button"
          onClick={onClose}
          className="mt-6 w-full rounded-button bg-accent px-4 py-2.5 font-medium text-white hover:bg-accent-hover transition-colors"
        >
          OK
        </button>
      </div>
    </div>
  );
}
