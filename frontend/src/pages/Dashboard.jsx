import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import CourseCard from '../components/CourseCard';
import TermSelector from '../components/TermSelector';
import { getCourses, createCourse } from '../api/client';

export default function Dashboard() {
  const [currentTermId, setCurrentTermId] = useState(null);
  const [courses, setCourses] = useState([]);
  const [loadingCourses, setLoadingCourses] = useState(false);
  const [courseError, setCourseError] = useState('');

  // Inline add-course form state
  const [adding, setAdding] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [saving, setSaving] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (adding && inputRef.current) inputRef.current.focus();
  }, [adding]);

  const handleTermChange = async termId => {
    setCurrentTermId(termId);
    setCourses([]);
    setCourseError('');
    if (!termId) return;
    setLoadingCourses(true);
    try {
      const data = await getCourses(termId);
      setCourses(data.courses || []);
    } catch (e) {
      setCourseError(e.message);
    } finally {
      setLoadingCourses(false);
    }
  };

  const handleAddCourse = async e => {
    e.preventDefault();
    const name = newCourseName.trim();
    if (!name || !currentTermId) return;
    setSaving(true);
    setCourseError('');
    try {
      const course = await createCourse(currentTermId, name);
      setCourses(prev => [...prev, course]);
      setNewCourseName('');
      setAdding(false);
    } catch (e) {
      setCourseError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-10">
      <div className="animate-fade-in">
        <h1 className="text-2xl font-semibold text-ink">Dashboard</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Your weekly overview and upcoming assignments.
        </p>
      </div>

      <div className="rounded-card bg-surface-elevated border border-border p-4 shadow-card animate-fade-in [animation-delay:100ms]">
        <TermSelector onTermChange={handleTermChange} />
      </div>

      <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card animate-fade-in [animation-delay:200ms]">
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
                  animationDelay: `${i * 120}ms`,
                }}
              />
              <span className="text-xs text-ink-subtle">{day}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-ink-subtle">
          Hours of work scheduled this week.
        </p>
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Upcoming (placeholder) */}
        <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card animate-fade-in-up [animation-delay:400ms]">
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
          <p className="text-sm text-ink-muted py-2">
            Upcoming assignments will appear here once schedule generation is
            implemented.
          </p>
        </section>

        {/* Courses section */}
        <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card animate-fade-in-up [animation-delay:700ms]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-ink">Courses</h2>
            {currentTermId && !adding && (
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="text-sm font-medium text-accent hover:text-accent-hover transition-colors duration-200"
              >
                + Add course
              </button>
            )}
          </div>

          {/* Inline add form */}
          {adding && (
            <form
              onSubmit={handleAddCourse}
              className="flex gap-2 mb-4 animate-fade-in"
            >
              <input
                ref={inputRef}
                type="text"
                value={newCourseName}
                onChange={e => setNewCourseName(e.target.value)}
                placeholder="e.g. CS 422"
                className="flex-1 rounded-input border border-border bg-surface px-3 py-1.5 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              />
              <button
                type="submit"
                disabled={saving || !newCourseName.trim()}
                className="rounded-button bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setAdding(false);
                  setNewCourseName('');
                }}
                className="rounded-button px-3 py-1.5 text-sm text-ink-muted hover:text-ink transition-colors"
              >
                Cancel
              </button>
            </form>
          )}

          {courseError && (
            <p className="text-sm text-red-500 mb-3">{courseError}</p>
          )}

          <div className="space-y-3">
            {!currentTermId ? (
              <p className="text-sm text-ink-muted py-4">
                Select a term above to view its courses.
              </p>
            ) : loadingCourses ? (
              <p className="text-sm text-ink-muted py-4 animate-pulse">
                Loading courses…
              </p>
            ) : courses.length === 0 ? (
              <p className="text-sm text-ink-muted py-4">
                No courses yet.{' '}
                <button
                  type="button"
                  onClick={() => setAdding(true)}
                  className="text-accent hover:text-accent-hover underline"
                >
                  Add a course
                </button>{' '}
                to get started.
              </p>
            ) : (
              courses.map((c, i) => (
                <div
                  key={c.id}
                  className="animate-fade-in-up"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <CourseCard course={c} />
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
