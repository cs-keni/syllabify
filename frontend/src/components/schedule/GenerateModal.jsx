/** Proposed study schedule preview modal. */
export default function GenerateModal({
  proposedSlots,
  applyingSchedule,
  onApply,
  onClose,
}) {
  const sorted = [...proposedSlots].sort(
    (a, b) => new Date(a.start_time) - new Date(b.start_time)
  );
  const merged = [];
  for (const s of sorted) {
    const last = merged[merged.length - 1];
    const sameCourse = last && last.course_name === s.course_name;
    const adjacent =
      last &&
      new Date(last.end_time).getTime() === new Date(s.start_time).getTime();
    if (sameCourse && adjacent) {
      last.end_time = s.end_time;
    } else {
      merged.push({ ...s });
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/45"
        onClick={() => !applyingSchedule && onClose()}
      />
      <div className="relative z-10 w-full max-w-xl rounded-xl border border-border bg-surface p-5 shadow-xl max-h-[85vh] flex flex-col">
        <h3 className="text-lg font-semibold text-ink">
          Proposed study schedule
        </h3>
        <p className="mt-1 text-sm text-ink-muted">
          Here&apos;s a proposed study schedule based on your availability,
          course workload, and calendar events. Unlocked blocks will be replaced
          when you apply.
        </p>
        <div className="mt-4 overflow-y-auto flex-1 min-h-0 rounded-lg border border-border bg-surface-muted/50 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted mb-2">
            {merged.length} block(s) · spread across your study window
          </p>
          <ul className="space-y-1.5 text-sm">
            {merged.slice(0, 50).map((s, i) => (
              <li key={i} className="flex items-center gap-2 text-ink">
                <span className="font-medium truncate flex-1">
                  {s.course_name || 'Study'}
                </span>
                <span className="text-ink-muted shrink-0 font-mono text-xs">
                  {new Date(s.start_time).toLocaleDateString(undefined, {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric',
                  })}{' '}
                  {new Date(s.start_time).toLocaleTimeString([], {
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                  –
                  {new Date(s.end_time).toLocaleTimeString([], {
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </span>
              </li>
            ))}
            {merged.length > 50 && (
              <li className="text-ink-muted text-xs">
                … and {merged.length - 50} more
              </li>
            )}
          </ul>
        </div>
        <div className="mt-4 flex gap-2 justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={applyingSchedule}
            className="rounded-lg border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-surface-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onApply}
            disabled={applyingSchedule}
            className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-inv hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {applyingSchedule ? 'Applying…' : 'Apply schedule'}
          </button>
        </div>
      </div>
    </div>
  );
}
