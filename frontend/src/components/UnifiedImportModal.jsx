import { useState, useEffect } from 'react';

const CATEGORIES = [
  { value: 'canvas', label: 'Canvas Calendar' },
  { value: 'academic', label: 'Academic / University' },
  { value: 'personal', label: 'Personal' },
  { value: 'work', label: 'Work' },
  { value: 'other', label: 'Other' },
];

export default function UnifiedImportModal({
  onClose,
  onImportGoogle,
  onImportIcs,
  token,
  getCalendarList,
  calendarConnected,
  activeTerm,
}) {
  const [activeTab, setActiveTab] = useState(
    calendarConnected ? 'google' : 'ics'
  );

  // Google Calendar tab state
  const [calendars, setCalendars] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loadingCals, setLoadingCals] = useState(false);

  // ICS tab state
  const [icsUrl, setIcsUrl] = useState('');
  const [icsLabel, setIcsLabel] = useState('');
  const [icsCategory, setIcsCategory] = useState('other');

  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');

  // Load Google calendars when tab switches to google
  useEffect(() => {
    if (activeTab === 'google' && calendarConnected && calendars.length === 0) {
      setLoadingCals(true);
      getCalendarList(token)
        .then(data => {
          setCalendars(data.calendars || []);
          const primary = data.calendars?.find(c => c.primary);
          if (primary) setSelected(new Set([primary.id]));
        })
        .catch(() => setError('Failed to load calendars'))
        .finally(() => setLoadingCals(false));
    }
  }, [activeTab, calendarConnected, token]);

  // Set date defaults from active term
  useEffect(() => {
    if (activeTerm?.start_date && activeTerm?.end_date) {
      setStartDate(activeTerm.start_date);
      setEndDate(activeTerm.end_date);
    } else {
      const now = new Date();
      setStartDate(now.toISOString().slice(0, 10));
      const future = new Date(now);
      future.setMonth(future.getMonth() + 3);
      setEndDate(future.toISOString().slice(0, 10));
    }
  }, [activeTerm]);

  const toggleCalendar = id => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleGoogleImport = async () => {
    if (selected.size === 0) return setError('Select at least one calendar');
    if (!startDate || !endDate) return setError('Select a date range');
    setImporting(true);
    setError('');
    try {
      await onImportGoogle({
        calendar_ids: Array.from(selected),
        start_date: startDate,
        end_date: endDate,
      });
      onClose();
    } catch (e) {
      setError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const handleIcsImport = async () => {
    if (!icsUrl.trim()) return setError('Enter a feed URL');
    if (!icsLabel.trim()) return setError('Enter a label for this calendar');
    setImporting(true);
    setError('');
    try {
      await onImportIcs({
        url: icsUrl.trim(),
        label: icsLabel.trim(),
        category: icsCategory,
      });
      onClose();
    } catch (e) {
      setError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 pt-5 pb-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Import Calendar
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Import events from Google Calendar or an ICS/iCal feed URL.
          </p>
        </div>

        {/* Tabs */}
        <div className="px-6 flex border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => {
              setActiveTab('google');
              setError('');
            }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === 'google'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Google Calendar
          </button>
          <button
            onClick={() => {
              setActiveTab('ics');
              setError('');
            }}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === 'ics'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            ICS / iCal Feed
          </button>
        </div>

        {/* Tab Content */}
        <div className="px-6 py-4">
          {activeTab === 'google' && (
            <div className="space-y-4">
              {!calendarConnected ? (
                <p className="text-sm text-gray-500">
                  Connect your Google account first from the Schedule page.
                </p>
              ) : loadingCals ? (
                <p className="text-sm text-gray-500">Loading calendars...</p>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Select calendars
                    </label>
                    <div className="max-h-40 overflow-y-auto border rounded-lg p-2 space-y-1 dark:border-gray-600">
                      {calendars.map(cal => (
                        <label
                          key={cal.id}
                          className="flex items-center gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selected.has(cal.id)}
                            onChange={() => toggleCalendar(cal.id)}
                            className="rounded text-blue-600"
                          />
                          <span className="text-sm text-gray-800 dark:text-gray-200 truncate">
                            {cal.summary} {cal.primary && '(Primary)'}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Start
                      </label>
                      <input
                        type="date"
                        value={startDate}
                        onChange={e => setStartDate(e.target.value)}
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        End
                      </label>
                      <input
                        type="date"
                        value={endDate}
                        onChange={e => setEndDate(e.target.value)}
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                      />
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'ics' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Feed URL
                </label>
                <input
                  type="url"
                  value={icsUrl}
                  onChange={e => setIcsUrl(e.target.value)}
                  placeholder="https://example.com/calendar.ics"
                  className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                />
                <p className="mt-1 text-xs text-gray-400">
                  Paste an ICS/iCal feed URL (e.g. Canvas Calendar Feed).
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Label
                </label>
                <input
                  type="text"
                  value={icsLabel}
                  onChange={e => setIcsLabel(e.target.value)}
                  placeholder="My Canvas Calendar"
                  className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Category
                </label>
                <select
                  value={icsCategory}
                  onChange={e => setIcsCategory(e.target.value)}
                  className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                >
                  {CATEGORIES.map(c => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            onClick={
              activeTab === 'google' ? handleGoogleImport : handleIcsImport
            }
            disabled={
              importing || (activeTab === 'google' && !calendarConnected)
            }
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {importing ? 'Importing...' : 'Import'}
          </button>
        </div>
      </div>
    </div>
  );
}
