/**
 * Weekly schedule grid (Mon–Sun, 24h). Fetches and displays study time blocks.
 */
import { useState, useEffect, useCallback } from 'react';

const HOURS = 24;
const DAYS = 7;
const LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const GRID_START_HOUR = 6; // 6am = top of visible area

/** Convert study_times from API to blocks for the grid. weekStart = Monday. */
function studyTimesToBlocks(studyTimes, weekStart) {
  if (!studyTimes?.length || !weekStart) return [];
  const blocks = [];
  const weekStartTime = new Date(weekStart);
  weekStartTime.setHours(0, 0, 0, 0);

  for (const st of studyTimes) {
    const startDt = new Date(st.start_time);
    const endDt = new Date(st.end_time);
    const startDate = new Date(startDt.getFullYear(), startDt.getMonth(), startDt.getDate());
    const dayDiff = Math.round((startDate - weekStartTime) / (24 * 60 * 60 * 1000));
    if (dayDiff < 0 || dayDiff >= DAYS) continue;

    const startHour =
      startDt.getHours() + startDt.getMinutes() / 60 + startDt.getSeconds() / 3600;
    const endHour =
      endDt.getHours() + endDt.getMinutes() / 60 + endDt.getSeconds() / 3600;

    blocks.push({
      id: st.id,
      day: dayDiff,
      start: startHour,
      end: endHour,
      title: 'Study',
      notes: st.notes,
    });
  }
  return blocks;
}

/** Renders a weekly schedule grid with time blocks. */
export default function SchedulePreview({
  weekStart,
  activeTerm,
  token,
  getStudyTimes,
  onRefresh,
}) {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const hourHeight = 48;

  const fetchBlocks = useCallback(() => {
    if (!token || !activeTerm?.id || !weekStart || !getStudyTimes) {
      setBlocks([]);
      return;
    }
    const start = new Date(weekStart);
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(end.getDate() + 7);
    const startStr = start.toISOString().slice(0, 10);
    const endStr = end.toISOString().slice(0, 10);

    setLoading(true);
    setError(null);
    getStudyTimes(token, activeTerm.id, startStr, endStr)
      .then(data => {
        const b = studyTimesToBlocks(data.study_times || [], weekStart);
        setBlocks(b);
      })
      .catch(e => {
        setError(e.message);
        setBlocks([]);
      })
      .finally(() => setLoading(false));
  }, [token, activeTerm?.id, weekStart, getStudyTimes]);

  useEffect(() => {
    fetchBlocks();
  }, [fetchBlocks]);

  // Expose refresh for parent (e.g. after generate)
  useEffect(() => {
    if (onRefresh) onRefresh.current = fetchBlocks;
  }, [onRefresh, fetchBlocks]);

  return (
    <div className="rounded-card bg-surface-elevated border border-border overflow-hidden shadow-card animate-fade-in [animation-delay:200ms]">
      <div className="grid grid-cols-8 border-b border-border bg-surface-muted">
        <div className="p-2 text-xs font-medium text-ink-muted" />
        {LABELS.map(d => (
          <div
            key={d}
            className="p-2 text-center text-xs font-medium text-ink border-l border-border"
          >
            {d}
          </div>
        ))}
      </div>
      {loading && (
        <div className="py-12 text-center text-sm text-ink-muted">
          Loading schedule…
        </div>
      )}
      {error && (
        <div className="py-4 px-4 text-sm text-amber-600 bg-amber-50 dark:bg-amber-950/30">
          {error}
        </div>
      )}
      {!activeTerm && !loading && (
        <div className="py-12 text-center text-sm text-ink-muted">
          Select a term to view your schedule.
        </div>
      )}
      {activeTerm && blocks.length === 0 && !loading && !error && (
        <div className="py-12 text-center text-sm text-ink-muted">
          No study blocks this week. Generate study times to create a schedule.
        </div>
      )}
      <div
        className="relative"
        style={{
          height: HOURS * hourHeight,
          display: loading || error || !activeTerm ? 'none' : 'block',
        }}
        aria-hidden={loading || error || !activeTerm}
      >
        {/* Hour lines */}
        {Array.from({ length: HOURS }, (_, i) => (
          <div
            key={i}
            className="absolute left-0 right-0 border-t border-border-subtle"
            style={{ top: i * hourHeight }}
          />
        ))}
        {/* Day columns */}
        {Array.from({ length: DAYS }, (_, i) => (
          <div
            key={i}
            className="absolute top-0 bottom-0 border-l border-border-subtle"
            style={{
              left: `${(100 / 8) * (i + 1)}%`,
              width: `${100 / 8}%`,
            }}
          />
        ))}
        {/* Blocks */}
        {blocks.map((b, i) => {
          const top = Math.max(0, (b.start - GRID_START_HOUR) * hourHeight);
          const bottom = (b.end - GRID_START_HOUR) * hourHeight;
          const height = Math.max(4, bottom - top - 2);
          return (
            <div
              key={b.id || i}
              className="absolute rounded flex items-center justify-center overflow-hidden text-[10px] origin-top-left animate-scale-in bg-accent/90 text-white"
              style={{
                left: `${(100 / 8) * (b.day + 1) + 2}%`,
                width: `${100 / 8 - 4}%`,
                top,
                height,
                animationDelay: `${i * 30}ms`,
              }}
              title={b.notes || b.title}
            >
              {b.title}
            </div>
          );
        })}
      </div>
      <div className="px-4 py-2 border-t border-border bg-surface-muted text-xs text-ink-muted">
        Study blocks from your generated schedule. Export to Google Calendar or
        download ICS when ready.
      </div>
    </div>
  );
}
