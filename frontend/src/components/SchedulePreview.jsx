/**
 * Weekly schedule grid (Mon–Sun, 24h). Fetches and displays study time blocks.
 * Google Calendar–style with time labels and editable blocks.
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const HOURS = 24;
const DAYS = 7;
const LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const GRID_START_HOUR = 6; // 6am = top of visible area

/** Format ISO string for datetime-local input (local time). */
function toDatetimeLocal(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${day}T${h}:${min}`;
}

/** Format hour as "9:00 AM" or "12:00 PM". */
function formatHour(hour) {
  const h = Math.floor(hour);
  const m = Math.round((hour - h) * 60);
  const period = h < 12 ? 'AM' : 'PM';
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${h12}:${m.toString().padStart(2, '0')} ${period}`;
}

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
      startTimeStr: formatHour(startHour),
      endTimeStr: formatHour(endHour),
      startTime: st.start_time,
      endTime: st.end_time,
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
  updateStudyTime,
  deleteStudyTime,
  onRefresh,
}) {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingBlock, setEditingBlock] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const popoverRef = useRef(null);
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

  // Close popover on outside click
  useEffect(() => {
    if (!editingBlock) return;
    const onClick = e => {
      if (popoverRef.current && !popoverRef.current.contains(e.target))
        setEditingBlock(null);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [editingBlock]);

  const handleSaveEdit = async () => {
    if (!editingBlock || !token || !updateStudyTime) return;
    const toIso = s => {
      if (!s) return s;
      return s.length === 16 ? `${s}:00` : s;
    };
    setSaving(true);
    try {
      await updateStudyTime(token, editingBlock.id, {
        start_time: toIso(editingBlock.editStart),
        end_time: toIso(editingBlock.editEnd),
        notes: editingBlock.editNotes ?? editingBlock.notes,
      });
      setEditingBlock(null);
      fetchBlocks();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!editingBlock || !token || !deleteStudyTime) return;
    if (!window.confirm('Remove this study block?')) return;
    setDeleting(true);
    try {
      await deleteStudyTime(token, editingBlock.id);
      setEditingBlock(null);
      fetchBlocks();
    } catch (e) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  const timeLabels = Array.from({ length: HOURS }, (_, i) => {
    const h = (i + GRID_START_HOUR) % 24;
    const period = h < 12 ? 'AM' : 'PM';
    const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${h12} ${period}`;
  });

  return (
    <div className="relative rounded-card bg-surface-elevated border border-border overflow-hidden shadow-card animate-fade-in [animation-delay:200ms]">
      <div className="flex border-b border-border bg-surface-muted">
        <div className="w-14 shrink-0 border-r border-border p-2 text-xs font-medium text-ink-muted" />
        <div className="flex-1 grid grid-cols-7">
          {LABELS.map(d => (
            <div
              key={d}
              className="p-2 text-center text-xs font-medium text-ink border-l border-border"
            >
              {d}
            </div>
          ))}
        </div>
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
        className="flex"
        style={{
          display: loading || error || !activeTerm ? 'none' : 'flex',
        }}
        aria-hidden={loading || error || !activeTerm}
      >
        {/* Time labels column */}
        <div
          className="w-14 shrink-0 border-r border-border bg-surface-muted/30 relative"
          style={{ height: HOURS * hourHeight }}
        >
          {timeLabels.map((label, i) => (
            <div
              key={i}
              className="absolute right-1 -translate-y-1/2 text-[10px] text-ink-muted tabular-nums"
              style={{ top: i * hourHeight + hourHeight / 2 }}
            >
              {label}
            </div>
          ))}
        </div>
        {/* Grid area */}
        <div
          className="flex-1 relative"
          style={{ height: HOURS * hourHeight }}
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
                left: `${(100 / 7) * i}%`,
                width: `${100 / 7}%`,
              }}
            />
          ))}
          {/* Blocks */}
          {blocks.map((b, i) => {
            const top = Math.max(0, (b.start - GRID_START_HOUR) * hourHeight);
            const bottom = (b.end - GRID_START_HOUR) * hourHeight;
            const height = Math.max(4, bottom - top - 2);
            const dayWidth = 100 / 7;
            return (
              <button
                key={b.id || i}
                type="button"
                onClick={e => {
                  e.stopPropagation();
                  setEditingBlock({
                    ...b,
                    editStart: toDatetimeLocal(b.startTime),
                    editEnd: toDatetimeLocal(b.endTime),
                    editNotes: b.notes || '',
                  });
                }}
                className="absolute rounded flex flex-col justify-center overflow-hidden text-[10px] origin-top-left animate-scale-in bg-accent/90 text-white px-1 py-0.5 text-left hover:bg-accent hover:ring-2 hover:ring-accent/50 transition-colors cursor-pointer"
                style={{
                  left: `${dayWidth * b.day + 2}%`,
                  width: `${dayWidth - 4}%`,
                  top,
                  height,
                  animationDelay: `${i * 30}ms`,
                }}
                title={`${b.startTimeStr} – ${b.endTimeStr} · Click to edit`}
              >
                <span className="font-medium truncate">{b.title}</span>
                <span className="text-[9px] opacity-90 truncate">
                  {b.startTimeStr} – {b.endTimeStr}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      {/* Edit popover */}
      {editingBlock && (
        <div
          ref={popoverRef}
          className="fixed z-20 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-card border border-border bg-surface-elevated shadow-dropdown p-4 min-w-[260px] animate-scale-in"
          onClick={e => e.stopPropagation()}
        >
          <h4 className="text-sm font-medium text-ink mb-3">Edit study block</h4>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-ink-muted mb-0.5">
                Start
              </label>
              <input
                type="datetime-local"
                value={editingBlock.editStart}
                onChange={e =>
                  setEditingBlock(prev => ({ ...prev, editStart: e.target.value }))
                }
                className="w-full rounded-input border border-border bg-surface px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-ink-muted mb-0.5">
                End
              </label>
              <input
                type="datetime-local"
                value={editingBlock.editEnd}
                onChange={e =>
                  setEditingBlock(prev => ({ ...prev, editEnd: e.target.value }))
                }
                className="w-full rounded-input border border-border bg-surface px-2 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-ink-muted mb-0.5">
                Notes (optional)
              </label>
              <input
                type="text"
                value={editingBlock.editNotes}
                onChange={e =>
                  setEditingBlock(prev => ({ ...prev, editNotes: e.target.value }))
                }
                placeholder="e.g. Chapter 3"
                className="w-full rounded-input border border-border bg-surface px-2 py-1.5 text-sm"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              type="button"
              onClick={handleSaveEdit}
              disabled={saving}
              className="rounded-button bg-accent px-3 py-1.5 text-sm text-white hover:bg-accent-hover disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-button border border-red-300 text-red-600 px-3 py-1.5 text-sm hover:bg-red-50 disabled:opacity-50"
            >
              {deleting ? '…' : 'Delete'}
            </button>
            <button
              type="button"
              onClick={() => setEditingBlock(null)}
              className="rounded-button border border-border px-3 py-1.5 text-sm text-ink-muted hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      {editingBlock && (
        <div
          className="fixed inset-0 z-10 bg-ink/20"
          onClick={() => setEditingBlock(null)}
          aria-hidden="true"
        />
      )}

      <div className="px-4 py-2 border-t border-border bg-surface-muted text-xs text-ink-muted">
        Study blocks from your generated schedule. Click a block to edit or
        delete. Export to Google Calendar or download ICS when ready.
      </div>
    </div>
  );
}
