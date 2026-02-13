/**
 * Preferences: work hours, preferred days, workload limits.
 * Simple controls (sliders, toggles). Future: theme, dark mode, per-course colors.
 * DISCLAIMER: Project structure may change. Backend integration TODO.
 */
export default function Preferences() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in">
        <h1 className="text-2xl font-semibold text-ink">Preferences</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Set work hours, preferred days, and workload limits. More options
          coming later.
        </p>
      </div>

      <div className="rounded-card bg-surface-elevated border border-border p-6 shadow-card space-y-8 max-w-xl animate-fade-in-up [animation-delay:200ms]">
        <section>
          <h2 className="text-sm font-medium text-ink mb-3">Work hours</h2>
          <div className="flex items-center gap-4">
            <label className="text-sm text-ink-muted">Start</label>
            <input
              type="time"
              defaultValue="09:00"
              className="rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            />
            <label className="text-sm text-ink-muted">End</label>
            <input
              type="time"
              defaultValue="17:00"
              className="rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            />
          </div>
        </section>

        <section>
          <h2 className="text-sm font-medium text-ink mb-3">Preferred days</h2>
          <div className="flex flex-wrap gap-2">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
              <label
                key={day}
                className="inline-flex items-center gap-2 rounded-button border border-border bg-surface px-3 py-2 text-sm text-ink cursor-pointer hover:bg-surface-muted has-[:checked]:border-accent has-[:checked]:bg-accent-muted"
              >
                <input
                  type="checkbox"
                  defaultChecked={day !== 'Sat' && day !== 'Sun'}
                  className="rounded border-border text-accent focus:ring-accent"
                />
                {day}
              </label>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-sm font-medium text-ink mb-3">
            Max hours per day
          </h2>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="2"
              max="12"
              defaultValue="8"
              className="w-48 h-2 rounded-full appearance-none bg-border accent-accent"
            />
            <span className="text-sm text-ink-muted">8 hours</span>
          </div>
        </section>

        <p className="text-xs text-ink-subtle">
          Calendar theme, dark mode, and per-course colors will be available in
          a future update.
        </p>
      </div>
    </div>
  );
}
