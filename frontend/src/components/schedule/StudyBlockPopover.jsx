/** Click popover for study blocks — lock/unlock/lock-day actions. */
export default function StudyBlockPopover({
  popover,
  onToggleLock,
  onLockDay,
  onClose,
}) {
  if (!popover) return null;
  const { studyTime, x, y } = popover;

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div
        className="fixed z-50 min-w-[180px] rounded-lg border border-border bg-surface p-3 text-sm shadow-lg"
        style={{ top: y + 8, left: x + 8 }}
      >
        <p className="mb-0.5 truncate font-medium text-ink">
          {studyTime.course_name || 'Study Block'}
        </p>
        {studyTime.assignment_name && (
          <p className="mb-1 truncate text-xs text-ink-muted">
            {studyTime.assignment_name}
          </p>
        )}
        <p className="mb-2 text-xs text-ink-muted">
          {studyTime.is_locked
            ? 'Locked — this block stays when you regenerate.'
            : 'Unlocked — will be replaced when you regenerate. Lock to keep it.'}
        </p>
        <div className="flex flex-col gap-1.5">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onToggleLock}
              className="flex-1 rounded bg-primary px-2 py-1 text-xs font-medium text-primary-inv hover:opacity-90"
            >
              {studyTime.is_locked ? 'Unlock' : 'Lock block'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-border px-2 py-1 text-xs text-ink-muted hover:text-ink"
            >
              Close
            </button>
          </div>
          <button
            type="button"
            onClick={onLockDay}
            className="w-full rounded border border-border px-2 py-1 text-xs text-ink-muted hover:bg-surface-muted hover:text-ink"
          >
            Lock entire day
          </button>
        </div>
      </div>
    </>
  );
}
