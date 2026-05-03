/** Schedule action buttons: Generate, Clear, Connect calendar, Export. */
import { Link } from 'react-router-dom';

export default function ScheduleToolbar({
  generating,
  clearingSchedule,
  calendarConnected,
  studyTimesCount,
  token,
  onGenerate,
  onClear,
  onConnectOrImport,
  onExport,
}) {
  return (
    <div className="animate-fade-in">
      <Link
        to="/app"
        className="text-sm text-ink-muted hover:text-ink transition-colors no-underline"
      >
        &larr; Dashboard
      </Link>
      <h1 className="mt-2 text-2xl font-semibold text-ink">Schedule</h1>
      <p className="mt-1 text-sm text-ink-muted">
        Your calendar events and study blocks at a glance. Study blocks appear in the date
        range of your assignments—use the calendar arrows to navigate.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onGenerate}
          disabled={generating || !token}
          className="px-4 py-2 rounded-lg bg-primary text-primary-inv font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          title="Keyboard shortcut: G"
        >
          {generating ? 'Generating…' : 'Generate Study Times'}
        </button>
        <button
          type="button"
          onClick={onClear}
          disabled={clearingSchedule || !token || studyTimesCount === 0}
          className="px-4 py-2 rounded-lg border border-border bg-surface text-ink font-medium text-sm hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {clearingSchedule ? 'Clearing…' : 'Clear study times'}
        </button>
        <button
          type="button"
          onClick={onConnectOrImport}
          disabled={!token}
          className="px-4 py-2 rounded-lg border border-border bg-surface text-ink font-medium text-sm hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {calendarConnected ? 'Import from Google Calendar' : 'Connect Google Calendar'}
        </button>
        <button
          type="button"
          onClick={onExport}
          disabled={!token}
          className="px-4 py-2 rounded-lg border border-border bg-surface text-ink font-medium text-sm hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          title="Keyboard shortcut: E"
        >
          iCal Export
        </button>
      </div>
    </div>
  );
}
