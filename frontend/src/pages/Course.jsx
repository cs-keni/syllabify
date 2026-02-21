import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getCourse, deleteCourse } from '../api/client';

function AssignmentRow({ assignment }) {
  const due = assignment.due_date
    ? new Date(assignment.due_date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      })
    : '—';
  const hours = ((assignment.work_load || 0) / 4).toFixed(1);
  return (
    <li className="flex items-center justify-between px-3 py-2 rounded-button border border-border-subtle bg-surface text-sm">
      <span className="font-medium text-ink">{assignment.assignment_name}</span>
      <span className="text-ink-muted shrink-0 ml-4">
        {due} · {hours}h
      </span>
    </li>
  );
}

export default function Course() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    getCourse(courseId)
      .then(data => setCourse(data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [courseId]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteCourse(courseId);
      navigate('/app', { replace: true });
    } catch (e) {
      setError(e.message);
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse text-sm text-ink-muted py-12 text-center">
        Loading course…
      </div>
    );
  }

  if (error || !course) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-500">{error || 'Course not found.'}</p>
        <Link to="/app" className="text-sm text-accent hover:text-accent-hover">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            to="/app"
            className="text-sm text-ink-muted hover:text-ink transition-colors no-underline"
          >
            ← Dashboard
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-ink">
            {course.course_name}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">{course.term_name}</p>
        </div>

        <div className="flex gap-2 shrink-0">
          <button
            type="button"
            onClick={() =>
              navigate('/app/upload', {
                state: {
                  courseId: course.id,
                  courseName: course.course_name,
                },
              })
            }
            className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
          >
            Upload syllabus
          </button>

          {!confirmDelete ? (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:text-red-500 hover:border-red-300 transition-colors"
            >
              Delete
            </button>
          ) : (
            <div className="flex gap-1 items-center">
              <span className="text-xs text-ink-muted">Sure?</span>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="rounded-button bg-red-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50 transition-colors"
              >
                {deleting ? 'Deleting…' : 'Yes, delete'}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="rounded-button px-3 py-1.5 text-sm text-ink-muted hover:text-ink transition-colors"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Assignments */}
      <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-ink">
            Assignments
            <span className="ml-2 text-xs font-normal text-ink-subtle bg-surface-muted rounded-button px-2 py-0.5">
              {course.assignments.length}
            </span>
          </h2>
          <button
            type="button"
            onClick={() =>
              navigate('/app/upload', {
                state: {
                  courseId: course.id,
                  courseName: course.course_name,
                },
              })
            }
            className="text-sm font-medium text-accent hover:text-accent-hover transition-colors"
          >
            + Upload syllabus
          </button>
        </div>

        {course.assignments.length === 0 ? (
          <div className="py-8 text-center space-y-3">
            <p className="text-sm text-ink-muted">No assignments yet.</p>
            <button
              type="button"
              onClick={() =>
                navigate('/app/upload', {
                  state: {
                    courseId: course.id,
                    courseName: course.course_name,
                  },
                })
              }
              className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
            >
              Upload syllabus to extract assignments
            </button>
          </div>
        ) : (
          <ul className="space-y-2">
            {course.assignments.map(a => (
              <AssignmentRow key={a.id} assignment={a} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
