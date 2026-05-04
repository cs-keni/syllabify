/** Schedule sidebar: pie chart, weekly burndown, calendar sources. */
const SOURCE_COLOR_OPTIONS = [
  { hex: '#EF4444', label: 'Red' },
  { hex: '#F97316', label: 'Orange' },
  { hex: '#F59E0B', label: 'Amber' },
  { hex: '#84CC16', label: 'Lime' },
  { hex: '#10B981', label: 'Green' },
  { hex: '#14B8A6', label: 'Teal' },
  { hex: '#06B6D4', label: 'Cyan' },
  { hex: '#3B82F6', label: 'Blue' },
  { hex: '#6366F1', label: 'Indigo' },
  { hex: '#8B5CF6', label: 'Violet' },
  { hex: '#EC4899', label: 'Pink' },
  { hex: '#64748B', label: 'Slate' },
];

const COURSE_COLORS = [
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#8B5CF6',
  '#EC4899',
  '#06B6D4',
  '#64748B',
];

export default function ScheduleSidebar({
  studyTimeByCourse,
  totalStudyMins,
  weeklyHours,
  sources,
  syncingId,
  colorEditId,
  onColorEditToggle,
  onColorChange,
  onSyncSource,
  onDeleteSource,
  onAddSource,
}) {
  return (
    <div className="w-full lg:w-64 shrink-0 order-2 space-y-4">
      {/* Time per course pie chart */}
      <div className="rounded-xl border border-border bg-surface-elevated p-4 shadow-card">
        <h3 className="text-sm font-semibold text-ink mb-2">Time per course</h3>
        {studyTimeByCourse.length > 0 ? (
          <div className="flex items-center gap-4 group/pie">
            <div
              className="w-20 h-20 rounded-full shrink-0 transition-transform duration-300 ease-out group-hover/pie:scale-110"
              style={{
                background: `conic-gradient(${studyTimeByCourse
                  .map((c, i) => {
                    const start = studyTimeByCourse
                      .slice(0, i)
                      .reduce((s, x) => s + (x.mins / totalStudyMins) * 100, 0);
                    const end = start + (c.mins / totalStudyMins) * 100;
                    return `${c.color || COURSE_COLORS[i % COURSE_COLORS.length]} ${start}% ${end}%`;
                  })
                  .join(', ')})`,
              }}
              title={studyTimeByCourse
                .map(c => `${c.name}: ${Math.round((c.mins / 60) * 10) / 10}h`)
                .join(', ')}
            />
            <div className="min-w-0 flex-1 space-y-1">
              {studyTimeByCourse.slice(0, 5).map((c, i) => (
                <div
                  key={c.name}
                  className="flex items-center gap-2 text-xs rounded px-1 -mx-1 hover:bg-surface-muted"
                  title={`${c.name}: ${Math.round((c.mins / 60) * 10) / 10} hours`}
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{
                      backgroundColor:
                        c.color || COURSE_COLORS[i % COURSE_COLORS.length],
                    }}
                  />
                  <span className="truncate text-ink">{c.name}</span>
                  <span className="text-ink-muted tabular-nums shrink-0">
                    {Math.round((c.mins / totalStudyMins) * 100)}%
                  </span>
                </div>
              ))}
              {studyTimeByCourse.length > 5 && (
                <div className="text-xs text-ink-subtle px-1">
                  + {studyTimeByCourse.length - 5} more course
                  {studyTimeByCourse.length - 5 !== 1 ? 's' : ''}
                </div>
              )}
            </div>
          </div>
        ) : (
          <p className="text-xs text-ink-muted">
            Add courses from your syllabus, then click{' '}
            <strong>Generate Study Times</strong> above to see a breakdown of
            study time per course.
          </p>
        )}
      </div>

      {/* Weekly burndown bar chart */}
      {weeklyHours.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-elevated p-4 shadow-card">
          <h3 className="text-sm font-semibold text-ink mb-3">
            Weekly study hours
          </h3>
          {(() => {
            const maxH = Math.max(...weeklyHours.map(w => w.hours), 1);
            return (
              <div className="flex items-end gap-0.5 h-16 w-full">
                {weeklyHours.map(({ week, hours, isPast }) => (
                  <div
                    key={week}
                    className="flex-1 min-w-0 rounded-t transition-all duration-300 hover:opacity-80"
                    style={{
                      height: `${Math.max((hours / maxH) * 100, 4)}%`,
                      backgroundColor: isPast
                        ? 'var(--color-ink-subtle, #94a3b8)'
                        : 'var(--color-accent, #0F8A4C)',
                      opacity: isPast ? 0.35 : 1,
                    }}
                    title={`Week of ${new Date(week + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}: ${hours}h`}
                  />
                ))}
              </div>
            );
          })()}
          <p className="mt-1.5 text-[10px] text-ink-muted">
            {weeklyHours.length} week{weeklyHours.length !== 1 ? 's' : ''} ·{' '}
            {Math.round((totalStudyMins / 60) * 10) / 10}h total
          </p>
        </div>
      )}

      {/* Calendar sources */}
      <div className="rounded-xl border border-border bg-surface-elevated p-4 shadow-card">
        <h3 className="text-sm font-semibold text-ink mb-3">Sources</h3>
        {sources.length === 0 ? (
          <p className="text-xs text-ink-muted">
            No sources yet. Import a calendar to get started.
          </p>
        ) : (
          <ul className="space-y-2">
            {sources.map(src => (
              <li
                key={src.id}
                className="flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className="relative shrink-0">
                    <button
                      type="button"
                      onClick={() => onColorEditToggle(src.id)}
                      className="w-5 h-5 rounded-full border-2 border-white dark:border-gray-800 shadow-sm hover:ring-2 hover:ring-accent/50 transition-all cursor-pointer"
                      style={{ backgroundColor: src.color || '#64748B' }}
                      title="Change color"
                    />
                    {colorEditId === src.id && (
                      <>
                        <div
                          className="fixed inset-0 z-40"
                          onClick={() => onColorEditToggle(null)}
                        />
                        <div className="absolute left-0 top-6 z-50 p-2 rounded-lg border border-border bg-surface shadow-lg min-w-[140px]">
                          <p className="text-[10px] font-medium text-ink-muted mb-1.5 uppercase tracking-wide">
                            Color
                          </p>
                          <div className="grid grid-cols-4 gap-1.5">
                            {SOURCE_COLOR_OPTIONS.map(({ hex, label }) => (
                              <button
                                key={hex}
                                type="button"
                                onClick={() => onColorChange(src.id, hex)}
                                className="w-7 h-7 rounded border border-border hover:scale-110 transition-transform"
                                style={{ backgroundColor: hex }}
                                title={label}
                              />
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-ink truncate">
                      {src.source_label}
                    </p>
                    <p className="text-[10px] text-ink-muted font-mono tabular-nums">
                      {src.event_count} events ·{' '}
                      {src.source_type === 'google' ? 'Google' : 'ICS'}
                    </p>
                  </div>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button
                    onClick={() => onSyncSource(src.id)}
                    disabled={syncingId === src.id}
                    title="Sync"
                    className="text-ink-muted hover:text-accent text-xs disabled:opacity-50 transition-colors"
                  >
                    ↻
                  </button>
                  <button
                    onClick={() => onDeleteSource(src.id)}
                    title="Remove"
                    className="text-ink-muted hover:text-red-600 text-xs transition-colors"
                  >
                    ×
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        <button
          onClick={onAddSource}
          className="mt-3 w-full text-xs font-medium text-accent hover:text-accent-hover transition-colors"
        >
          + Add Source
        </button>
      </div>
    </div>
  );
}
