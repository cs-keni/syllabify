/**
 * Easter egg modal: confetti + message when user unlocks rainbow theme.
 */
import { useEffect } from 'react';
import confetti from 'canvas-confetti';

export default function RainbowEasterEggModal({ onClose }) {
  useEffect(() => {
    const duration = 3 * 1000;
    const end = Date.now() + duration;

    const frame = () => {
      confetti({
        particleCount: 3,
        angle: 60,
        spread: 55,
        origin: { x: 0 },
        colors: ['#ff0000', '#ff7f00', '#ffff00', '#00ff00', '#0000ff', '#4b0082', '#8f00ff'],
      });
      confetti({
        particleCount: 3,
        angle: 120,
        spread: 55,
        origin: { x: 1 },
        colors: ['#ff0000', '#ff7f00', '#ffff00', '#00ff00', '#0000ff', '#4b0082', '#8f00ff'],
      });
      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    };
    frame();

    const t = setTimeout(() => {
      confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
    }, 500);

    return () => clearTimeout(t);
  }, []);

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden
      />
      <div
        className="relative z-10 max-w-md rounded-2xl border-2 border-amber-400 bg-surface-elevated p-6 shadow-2xl animate-scale-in"
        role="dialog"
        aria-labelledby="easter-egg-title"
        aria-modal="true"
      >
        <h2 id="easter-egg-title" className="text-xl font-bold text-ink">
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
