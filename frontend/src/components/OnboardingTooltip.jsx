/**
 * Three-step onboarding overlay shown once to new users.
 * State persisted in localStorage under 'syllabify_onboarding_done'.
 */
import { useState, useEffect } from 'react';

const STORAGE_KEY = 'syllabify_onboarding_done';

const STEPS = [
  {
    title: 'Welcome to Syllabify!',
    body: 'Start by creating a term for your current semester — it groups all your courses together.',
    cta: 'Got it',
    icon: '🎓',
  },
  {
    title: 'Upload a syllabus',
    body: 'Go to Upload syllabus, drop in a PDF or paste text. AI will extract every assignment and deadline for you.',
    cta: 'Next',
    icon: '📄',
  },
  {
    title: 'Generate your schedule',
    body: 'Head to Schedule and click "Generate Study Times." A balanced plan fills your calendar automatically.',
    cta: "Let's go",
    icon: '📅',
  },
];

export default function OnboardingTooltip() {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      // Small delay so it doesn't flash during page load
      const t = setTimeout(() => setVisible(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1');
    setVisible(false);
  };

  const next = () => {
    if (step < STEPS.length - 1) {
      setStep(s => s + 1);
    } else {
      dismiss();
    }
  };

  if (!visible) return null;

  const current = STEPS[step];

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 animate-fade-in">
      <div
        className="absolute inset-0 bg-ink/20"
        onClick={dismiss}
        aria-hidden
      />
      <div className="relative z-10 w-full max-w-sm rounded-2xl border border-border bg-surface-elevated shadow-dropdown p-6 animate-scale-in">
        {/* Progress dots */}
        <div className="flex gap-1.5 mb-4">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === step ? 'w-6 bg-accent' : 'w-1.5 bg-border'
              }`}
            />
          ))}
        </div>

        <span className="text-3xl" aria-hidden>{current.icon}</span>
        <h3 className="mt-3 text-base font-semibold text-ink">{current.title}</h3>
        <p className="mt-2 text-sm text-ink-muted leading-relaxed">{current.body}</p>

        <div className="mt-5 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={dismiss}
            className="text-xs text-ink-subtle hover:text-ink-muted transition-colors"
          >
            Skip tour
          </button>
          <button
            type="button"
            onClick={next}
            className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          >
            {current.cta}
          </button>
        </div>
      </div>
    </div>
  );
}
