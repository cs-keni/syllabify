/**
 * Keyboard shortcuts overlay. Shows on ? key. Esc to close.
 */
import { useEffect } from 'react';

const SHORTCUTS = [
  { keys: ['?'], desc: 'Show this shortcuts overlay' },
  { keys: ['Esc'], desc: 'Close modal / dropdown' },
  { keys: ['g', 'd'], desc: 'Go to Dashboard' },
  { keys: ['g', 'u'], desc: 'Go to Upload syllabus' },
  { keys: ['g', 's'], desc: 'Go to Schedule' },
  { keys: ['g', 'p'], desc: 'Go to Preferences' },
];

export default function ShortcutsOverlay({ open, onClose }) {
  useEffect(() => {
    if (!open) return;
    const onKey = e => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 animate-fade-in"
      onClick={onClose}
      onKeyDown={e => e.key === 'Escape' && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-title"
    >
      <div
        className="rounded-card bg-surface-elevated border border-border shadow-dropdown p-6 max-w-md mx-4 animate-scale-in"
        onClick={e => e.stopPropagation()}
      >
        <h2 id="shortcuts-title" className="text-lg font-semibold text-ink mb-4">
          Keyboard shortcuts
        </h2>
        <dl className="space-y-3">
          {SHORTCUTS.map(({ keys, desc }, i) => (
            <div key={i} className="flex items-center justify-between gap-4">
              <dt className="text-sm text-ink-muted">{desc}</dt>
              <dd className="flex gap-1">
                {keys.map(k => (
                  <kbd
                    key={k}
                    className="rounded px-2 py-0.5 text-xs font-mono bg-surface-muted border border-border text-ink"
                  >
                    {k}
                  </kbd>
                ))}
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-xs text-ink-subtle">
          Press Esc to close
        </p>
      </div>
    </div>
  );
}
