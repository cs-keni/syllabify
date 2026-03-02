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

export default function CourseCard({ course }) {
  const { id, course_name, assignment_count, color } = course;
  const borderColor = color || COURSE_COLORS[(id || 0) % COURSE_COLORS.length];
  return (
    <Link
      to={`/app/courses/${id}`}
      className="block rounded-card border-l-4 border border-border bg-surface p-4 shadow-card no-underline text-ink hover:border-accent/40 hover:shadow-dropdown hover:scale-[1.02] hover:-translate-y-0.5 transition-all duration-200 ease-out"
      style={{ borderLeftColor: borderColor }}
    >
      <div className="flex items-start justify-between">
        <h3 className="font-medium text-ink">{course_name}</h3>
        <span className="text-xs text-ink-subtle bg-surface-muted rounded-button px-2 py-1 shrink-0 ml-2">
          {assignment_count ?? 0}{' '}
          {assignment_count === 1 ? 'assignment' : 'assignments'}
        </span>
      </div>
    </Link>
  );
}
