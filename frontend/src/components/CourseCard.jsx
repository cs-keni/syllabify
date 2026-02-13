/**
 * Card displaying course name, term, assignment count. Links to Schedule.
 * DISCLAIMER: Project structure may change. Props/behavior may be modified.
 */
import { Link } from 'react-router-dom';

/** Renders a single course card. Expects course: { name, term, assignmentCount }. */
export default function CourseCard({ course }) {
  const { name, term, assignmentCount } = course;
  return (
    <Link
      to="/app/schedule"
      className="block rounded-card border border-border bg-surface p-4 shadow-card no-underline text-ink hover:border-accent/40 hover:shadow-dropdown hover:scale-[1.02] hover:-translate-y-0.5 transition-all duration-200 ease-out"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-medium text-ink">{name}</h3>
          <p className="text-sm text-ink-muted mt-0.5">{term}</p>
        </div>
        <span className="text-xs text-ink-subtle bg-surface-muted rounded-button px-2 py-1">
          {assignmentCount} assignments
        </span>
      </div>
    </Link>
  );
}
