/**
 * Schedule page. Displays weekly schedule via SchedulePreview.
 * DISCLAIMER: Project structure may change.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import SchedulePreview from '../components/SchedulePreview';

/** Renders schedule page with weekStart (Monday of current week) and SchedulePreview. */
export default function Schedule() {
  const [weekStart] = useState(() => {
    const d = new Date();
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
  });

  return (
    <div className="space-y-8">
      <div className="animate-fade-in">
        <Link
          to="/app"
          className="text-sm text-ink-muted hover:text-ink transition-colors no-underline"
        >
          ← Dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-ink">Schedule</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Weekly view of your study blocks. Conflicts are highlighted subtly.
        </p>
      </div>
      <SchedulePreview weekStart={weekStart} />
    </div>
  );
}
