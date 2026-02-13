/**
 * Weekly schedule grid (Mon–Sun, 24h). Renders time blocks. Uses mock data (real API TODO).
 * DISCLAIMER: Project structure may change. Functions may be added or modified.
 */
const HOURS = 24;
const DAYS = 7;
const LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const COLOR_CLASSES = {
  'course-1': 'bg-course-1 text-ink',
  'course-2': 'bg-course-2 text-ink',
  'course-3': 'bg-course-3 text-ink',
  'course-4': 'bg-course-4 text-ink',
  'course-5': 'bg-course-5 text-ink',
};

const MOCK_BLOCKS = [
  {
    day: 0,
    start: 9,
    end: 11,
    title: 'CS 422',
    color: 'course-1',
    conflict: false,
  },
  {
    day: 0,
    start: 14,
    end: 16,
    title: 'CS 422',
    color: 'course-1',
    conflict: false,
  },
  {
    day: 1,
    start: 10,
    end: 12,
    title: 'CS 422',
    color: 'course-1',
    conflict: false,
  },
  {
    day: 2,
    start: 9,
    end: 10,
    title: 'CS 422',
    color: 'course-1',
    conflict: true,
  },
  {
    day: 2,
    start: 9.5,
    end: 11,
    title: 'Other',
    color: 'course-2',
    conflict: true,
  },
  {
    day: 3,
    start: 13,
    end: 15,
    title: 'CS 422',
    color: 'course-1',
    conflict: false,
  },
  {
    day: 4,
    start: 11,
    end: 12,
    title: 'CS 422',
    color: 'course-1',
    conflict: false,
  },
];

/** Renders a weekly schedule grid with time blocks. weekStart: Date for the week. */
export default function SchedulePreview({ weekStart }) {
  const hourHeight = 48;

  return (
    <div className="rounded-card bg-surface-elevated border border-border overflow-hidden shadow-card animate-fade-in [animation-delay:100ms]">
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
      <div className="relative" style={{ height: HOURS * hourHeight }}>
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
        {MOCK_BLOCKS.map((b, i) => (
          <div
            key={i}
            className={`absolute rounded flex items-center justify-center overflow-hidden text-[10px] origin-top-left animate-scale-in ${
              b.conflict
                ? 'bg-conflict border-2 border-red-300 text-red-800'
                : COLOR_CLASSES[b.color] || 'bg-course-1 text-ink'
            }`}
            style={{
              left: `${(100 / 8) * (b.day + 1) + 2}%`,
              width: `${100 / 8 - 4}%`,
              top: (b.start - 6) * hourHeight,
              height: (b.end - b.start) * hourHeight - 2,
              animationDelay: `${i * 30}ms`,
            }}
          >
            {b.conflict ? 'Conflict' : b.title}
          </div>
        ))}
      </div>
      <div className="px-4 py-2 border-t border-border bg-surface-muted text-xs text-ink-muted">
        Conflicts shown in light red. Export to Google Calendar or download ICS
        when ready.
      </div>
    </div>
  );
}
