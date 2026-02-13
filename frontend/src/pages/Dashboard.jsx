/**
 * Dashboard: weekly overview, upcoming assignments, course cards. Uses placeholder data.
 * DISCLAIMER: Project structure may change. Functions may be added or modified.
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import CourseCard from '../components/CourseCard';

const PLACEHOLDER_MODAL_KEY = 'syllabify_placeholder_modal_dismissed';

const MOCK_COURSES = [
  {
    id: '1',
    name: 'CS 422 (Placeholder)',
    term: 'Winter 2025',
    assignmentCount: 8,
  },
  {
    id: '2',
    name: 'CS 422 (Placeholder)',
    term: 'Winter 2025',
    assignmentCount: 8,
  },
];

const MOCK_UPCOMING = [
  {
    id: '1',
    title: 'Assignment 3 (Placeholder)',
    course: 'CS 422',
    due: 'Feb 2',
    hours: 4,
  },
  {
    id: '2',
    title: 'Reading quiz (Placeholder)',
    course: 'CS 422',
    due: 'Feb 4',
    hours: 1,
  },
  {
    id: '3',
    title: 'Lab 2 (Placeholder)',
    course: 'CS 422',
    due: 'Feb 6',
    hours: 3,
  },
];

/** Main dashboard. Shows placeholder weekly chart, upcoming list, and courses. */
export default function Dashboard() {
  const [showPlaceholderModal, setShowPlaceholderModal] = useState(false);

  useEffect(() => {
    const dismissed = sessionStorage.getItem(PLACEHOLDER_MODAL_KEY);
    if (!dismissed) setShowPlaceholderModal(true);
  }, []);

  /** Dismisses placeholder notice and stores in sessionStorage. */
  const closePlaceholderModal = () => {
    sessionStorage.setItem(PLACEHOLDER_MODAL_KEY, '1');
    setShowPlaceholderModal(false);
  };

  return (
    <div className="space-y-10">
      {showPlaceholderModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/20 animate-fade-in"
          onClick={closePlaceholderModal}
          onKeyDown={e => e.key === 'Escape' && closePlaceholderModal()}
          role="presentation"
        >
          <div
            className="rounded-card bg-surface-elevated border border-border shadow-dropdown p-4 max-w-md mx-4 animate-scale-in"
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <p className="text-sm text-ink mb-3">
              These are placeholder values to show an example of what the page
              might look like. They will be replaced with real data once we have a
              working backend.
            </p>
            <button
              type="button"
              onClick={closePlaceholderModal}
              className="rounded-button bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover transition-colors duration-200"
            >
              Close
            </button>
          </div>
        </div>
      )}

      <div className="animate-fade-in">
        <h1 className="text-2xl font-semibold text-ink">Dashboard</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Your weekly overview and upcoming assignments.
        </p>
      </div>

      <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card animate-fade-in [animation-delay:100ms]">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-sm font-medium text-ink">This week</h2>
          <span className="text-xs text-ink-subtle bg-surface-muted rounded-button px-2 py-0.5">
            Placeholder
          </span>
        </div>
        <div className="flex gap-4 items-end">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, i) => (
            <div key={day} className="flex-1 flex flex-col items-center gap-1">
              <div
                className="w-full rounded-t min-h-[4px] bg-accent-muted max-h-24 origin-bottom animate-bar-grow"
                style={{
                  height: `${[4, 6, 2, 5, 3, 0, 0][i]}rem`,
                  animationDelay: `${i * 60}ms`,
                }}
              />
              <span className="text-xs text-ink-subtle">{day}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-ink-muted">
          Balanced: ~20 hours across 5 days. (Placeholder)
        </p>
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card animate-fade-in-up [animation-delay:200ms]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium text-ink">Upcoming</h2>
              <span className="text-xs text-ink-subtle bg-surface-muted rounded-button px-2 py-0.5">
                Placeholder
              </span>
            </div>
            <Link
              to="/app/schedule"
              className="text-sm font-medium text-accent no-underline hover:text-accent-hover transition-colors duration-200"
            >
              View schedule
            </Link>
          </div>
          <ul className="space-y-2">
            {MOCK_UPCOMING.map((a, i) => (
              <li
                key={a.id}
                className="flex items-center justify-between rounded-button border border-border-subtle bg-surface px-3 py-2 text-sm animate-fade-in-up"
                style={{ animationDelay: `${240 + i * 40}ms` }}
              >
                <span className="font-medium text-ink">{a.title}</span>
                <span className="text-ink-muted">
                  {a.due} · {a.hours}h
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card animate-fade-in-up [animation-delay:350ms]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium text-ink">Courses</h2>
              <span className="text-xs text-ink-subtle bg-surface-muted rounded-button px-2 py-0.5">
                Placeholder
              </span>
            </div>
            <Link
              to="/app/upload"
              className="text-sm font-medium text-accent no-underline hover:text-accent-hover transition-colors duration-200"
            >
              Add syllabus
            </Link>
          </div>
          <div className="space-y-3">
            {MOCK_COURSES.length ? (
              MOCK_COURSES.map((c, i) => (
                <div
                  key={c.id}
                  className="animate-fade-in-up"
                  style={{ animationDelay: `${390 + i * 50}ms` }}
                >
                  <CourseCard course={c} />
                </div>
              ))
            ) : (
              <p className="text-sm text-ink-muted py-4">
                No courses yet. Upload a syllabus to get started.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
