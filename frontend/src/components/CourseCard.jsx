/**
 * Card displaying course name, term, assignment count. Links to Schedule. Optional delete.
 */
import { Link } from 'react-router-dom';

/** Renders a single course card. Expects course: { id?, name, term?, assignmentCount }; onDelete optional. */
export default function CourseCard({ course, onDelete }) {
  const { name, term, assignmentCount } = course;
  return (
    <div className="flex items-center gap-2 rounded-card border border-border bg-surface p-4 shadow-card hover:border-accent/40 hover:shadow-dropdown transition-all duration-200 ease-out">
      <Link
        to="/app/schedule"
        className="flex-1 min-w-0 no-underline text-ink hover:text-accent transition-colors"
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-medium text-ink">{name}</h3>
            {term && <p className="text-sm text-ink-muted mt-0.5">{term}</p>}
          </div>
          <span className="text-xs text-ink-subtle bg-surface-muted rounded-button px-2 py-1 shrink-0 ml-2">
            {assignmentCount} assignments
          </span>
        </div>
      </Link>
      {onDelete && (
        <button
          type="button"
          onClick={e => {
            e.preventDefault();
            onDelete();
          }}
          className="rounded-button px-2 py-1 text-xs text-red-600 hover:bg-red-500/10 transition-colors shrink-0"
          title="Delete course"
        >
          Delete
        </button>
      )}
    </div>
  );
}
