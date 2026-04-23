import { Link } from 'react-router-dom';

const COURSE_COLORS = [
  '#0f8a4c',
  '#2563eb',
  '#7c3aed',
  '#dc2626',
  '#ea580c',
  '#ca8a04',
  '#059669',
  '#0891b2',
];

export default function CourseCard({ course, onDelete }) {
  const { id, course_name, assignment_count, color } = course;
  const borderColor = color || COURSE_COLORS[(id || 0) % COURSE_COLORS.length];
  return (
    <div className="group relative">
      <Link
        to={`/app/courses/${id}`}
        className="block rounded-card border-l-4 border border-border bg-surface p-4 shadow-card no-underline text-ink hover:border-accent/40 hover:shadow-dropdown hover:scale-[1.02] hover:-translate-y-0.5 transition-all duration-200 ease-out"
        style={{ borderLeftColor: borderColor }}
      >
        <div className="flex items-start justify-between pr-6">
          <h3 className="font-medium text-ink">{course_name}</h3>
          <span className="text-xs text-ink-subtle bg-surface-muted rounded-button px-2 py-1 shrink-0 ml-2">
            {assignment_count ?? 0}{' '}
            {assignment_count === 1 ? 'assignment' : 'assignments'}
          </span>
        </div>
      </Link>
      {onDelete && (
        <button
          type="button"
          onClick={e => { e.preventDefault(); onDelete(); }}
          className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 rounded-button p-1.5 text-ink-subtle hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all duration-150"
          title="Delete course"
          aria-label={`Delete ${course_name}`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </button>
      )}
    </div>
  );
}
