/**
 * Modal for importing from Google Calendar. Calendar picker + date range.
 */
import { useState, useEffect } from 'react';

export default function CalendarImportModal({
  onClose,
  onImport,
  token,
  getCalendarList,
  activeTerm,
}) {
  const [calendars, setCalendars] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    getCalendarList(token)
      .then(data => {
        setCalendars(data.calendars || []);
        if (data.calendars?.length) {
          const primary = data.calendars.find(c => c.primary);
          if (primary) setSelected(new Set([primary.id]));
        }
      })
      .catch(err => setError(err.message || 'Failed to load calendars'))
      .finally(() => setLoading(false));
  }, [token, getCalendarList]);

  useEffect(() => {
    if (activeTerm?.start_date && activeTerm?.end_date) {
      setStartDate(activeTerm.start_date);
      setEndDate(activeTerm.end_date);
    } else {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      const end = new Date(now.getFullYear(), now.getMonth() + 3, 0);
      setStartDate(start.toISOString().slice(0, 10));
      setEndDate(end.toISOString().slice(0, 10));
    }
  }, [activeTerm]);

  const toggle = id => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleImport = async () => {
    if (selected.size === 0) {
      setError('Select at least one calendar');
      return;
    }
    if (!startDate || !endDate) {
      setError('Select date range');
      return;
    }
    setImporting(true);
    setError('');
    try {
      await onImport({
        calendar_ids: Array.from(selected),
        start_date: startDate,
        end_date: endDate,
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="calendar-import-title"
    >
      <div
        className="bg-surface-elevated border border-border rounded-2xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-6">
          <h2 id="calendar-import-title" className="text-lg font-semibold text-ink">
            Import from Google Calendar
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            Select calendars and date range. Events will be used to avoid scheduling conflicts.
          </p>

          {loading ? (
            <p className="mt-4 text-sm text-ink-muted">Loading calendars…</p>
          ) : (
            <>
              <div className="mt-4">
                <label className="block text-sm font-medium text-ink mb-2">Calendars</label>
                <div className="space-y-2 max-h-40 overflow-y-auto border border-border rounded-lg p-2">
                  {calendars.map(cal => (
                    <label
                      key={cal.id}
                      className="flex items-center gap-2 cursor-pointer hover:bg-surface-muted/50 rounded px-2 py-1.5"
                    >
                      <input
                        type="checkbox"
                        checked={selected.has(cal.id)}
                        onChange={() => toggle(cal.id)}
                        className="rounded border-border"
                      />
                      <span className="text-sm text-ink truncate">
                        {cal.summary || cal.id}
                        {cal.primary && (
                          <span className="text-ink-muted text-xs ml-1">(primary)</span>
                        )}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">Start date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={e => setStartDate(e.target.value)}
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink mb-1">End date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={e => setEndDate(e.target.value)}
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </>
          )}

          {error && (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          <div className="mt-6 flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-button border border-border bg-surface text-ink text-sm font-medium hover:bg-surface-muted"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleImport}
              disabled={loading || importing || selected.size === 0}
              className="px-4 py-2 rounded-button bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-50"
            >
              {importing ? 'Importing…' : 'Import'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
