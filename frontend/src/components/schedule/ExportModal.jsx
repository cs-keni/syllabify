/** iCal export modal. */
export default function ExportModal({
  loading,
  feedUrl,
  enabled,
  error,
  onCopy,
  onClose,
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/45" onClick={onClose} />
      <div className="relative z-10 w-full max-w-xl rounded-xl border border-border bg-surface p-5 shadow-xl">
        <h3 className="text-lg font-semibold text-ink">iCal Export</h3>
        <p className="mt-1 text-sm text-ink-muted">
          Subscribe this private feed URL in Apple Calendar / Google Calendar.
        </p>

        {loading ? (
          <p className="mt-4 text-sm text-ink-muted">Loading feed URL...</p>
        ) : error ? (
          <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        ) : (
          <>
            <div className="mt-4 rounded-lg border border-border bg-surface-muted p-3">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-muted">
                Your Feed URL
              </p>
              <p className="break-all text-xs text-ink">
                {feedUrl || 'No feed URL available'}
              </p>
            </div>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={onCopy}
                disabled={!feedUrl}
                className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-inv hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Copy URL
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-border px-3 py-2 text-xs font-medium text-ink hover:bg-surface-muted"
              >
                Close
              </button>
            </div>
            <p className="mt-3 text-xs text-ink-muted">
              {enabled
                ? 'Feed is enabled. Changes may take some time to appear in subscribed calendar apps.'
                : 'Feed is currently disabled.'}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
