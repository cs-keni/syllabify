import { Link } from 'react-router-dom';

export default function CourseCard({ course }) {
  const { id, course_name, assignment_count } = course;
  return (
    <Link
      to={`/app/courses/${id}`}
      className="block rounded-card border border-border bg-surface p-4 shadow-card no-underline text-ink hover:border-accent/40 hover:shadow-dropdown hover:scale-[1.02] hover:-translate-y-0.5 transition-all duration-200 ease-out"
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
