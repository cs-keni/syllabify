/**
 * Dashboard: weekly overview, upcoming assignments, course cards.
 */
import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getCourses, createCourse, deleteCourse } from '../api/client';
import CourseCard from '../components/CourseCard';
import TermSelector from '../components/TermSelector';

const PLACEHOLDER_MODAL_KEY = 'syllabify_placeholder_modal_dismissed';

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

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

/** Main dashboard. Shows placeholder weekly chart, upcoming list, and courses. */
export default function Dashboard() {
  const { user, token } = useAuth();
  const [showPlaceholderModal, setShowPlaceholderModal] = useState(false);
  const [courses, setCourses] = useState([]);
  const [coursesError, setCoursesError] = useState(null);
  const [currentTermId, setCurrentTermId] = useState(null);
  const [loadingCourses, setLoadingCourses] = useState(false);
  const [courseError, setCourseError] = useState('');
  const [adding, setAdding] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [saving, setSaving] = useState(false);
  const [sortBy, setSortBy] = useState('name');
  const inputRef = useRef(null);
  const [recentCourses, setRecentCourses] = useState([]);

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('syllabify_recent_courses') || '[]');
      setRecentCourses(stored.filter(c => c.id && c.course_name));
    } catch (_) {
      setRecentCourses([]);
    }
  }, [courses]);

  const sortedCourses = [...courses].sort((a, b) => {
    if (sortBy === 'name') return (a.course_name || '').localeCompare(b.course_name || '');
    const ac = a.assignment_count ?? 0;
    const bc = b.assignment_count ?? 0;
    return sortBy === 'count-desc' ? bc - ac : ac - bc;
  });

  const closePlaceholderModal = () => {
    setShowPlaceholderModal(false);
    try {
      localStorage.setItem(PLACEHOLDER_MODAL_KEY, '1');
    } catch (_) {}
  };

  // Courses load when term changes (via handleTermChange from TermSelector)

  const handleDeleteCourse = async id => {
    if (!token) return;
    try {
      await deleteCourse(id);
      setCourses(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      setCoursesError(err.message || 'Could not delete');
    }
  };

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
    <div className="space-y-6 sm:space-y-10">
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
              might look like. They will be replaced with real data once we have
              a working backend.
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
        <h1 className="text-2xl font-semibold text-ink">
          {user?.username ? `${getGreeting()}, ${user.username}` : 'Dashboard'}
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Your weekly overview and upcoming assignments.
        </p>
      </div>

      <div className="rounded-card bg-surface-elevated border border-border p-3 sm:p-4 shadow-card animate-fade-in [animation-delay:100ms]">
        <TermSelector onTermChange={handleTermChange} />
      </div>

      <section className="rounded-card bg-surface-elevated border border-border p-4 sm:p-6 shadow-card animate-fade-in [animation-delay:200ms]">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-sm font-medium text-ink">This week</h2>
          <span className="text-xs text-ink-subtle bg-surface-muted rounded-button px-2 py-0.5">
            Placeholder
          </span>
        </div>
        <div className="overflow-x-auto">
          <div className="flex gap-4 items-end min-w-[420px]">
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
        </div>
        <p className="mt-3 text-xs text-ink-subtle">
          Hours of work scheduled this week.
        </p>
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Upcoming (placeholder) */}
        <section className="rounded-card bg-surface-elevated border border-border p-4 sm:p-6 shadow-card animate-fade-in-up [animation-delay:400ms]">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
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
        <section className="rounded-card bg-surface-elevated border border-border p-4 sm:p-6 shadow-card animate-fade-in-up [animation-delay:700ms]">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <h2 className="text-sm font-medium text-ink">Courses</h2>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <label htmlFor="sort-courses" className="text-xs text-ink-muted">Sort:</label>
              <select
                id="sort-courses"
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
                className="rounded-input border border-border bg-surface px-2 py-1 text-xs flex-1 sm:flex-none"
              >
                <option value="name">Name</option>
                <option value="count-desc">Assignments (most)</option>
                <option value="count-asc">Assignments (least)</option>
              </select>
            </div>
            {currentTermId && !adding && (
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="text-sm font-medium text-accent hover:text-accent-hover transition-colors duration-200 self-start sm:self-auto"
              >
                + Add course
              </button>
            )}
          </div>

          {/* Inline add form */}
          {adding && (
            <form
              onSubmit={handleAddCourse}
              className="flex flex-col sm:flex-row gap-2 mb-4 animate-fade-in"
            >
              <input
                ref={inputRef}
                type="text"
                value={newCourseName}
                onChange={e => setNewCourseName(e.target.value)}
                placeholder="e.g. CS 422"
                className="w-full sm:flex-1 rounded-input border border-border bg-surface px-3 py-1.5 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
              />
              <button
                type="submit"
                disabled={saving || !newCourseName.trim()}
                className="rounded-button bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50 transition-colors w-full sm:w-auto"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setAdding(false);
                  setNewCourseName('');
                }}
                className="rounded-button px-3 py-1.5 text-sm text-ink-muted hover:text-ink transition-colors w-full sm:w-auto"
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
              <div className="py-8 text-center rounded-button border border-dashed border-border bg-surface-muted/50">
                <p className="text-sm text-ink-muted mb-2">Select a term above to view its courses.</p>
                <p className="text-xs text-ink-subtle">Choose an existing term or create a new one.</p>
              </div>
            ) : loadingCourses ? (
              <>
                {[1, 2, 3].map(i => (
                  <div key={i} className="rounded-card border border-border bg-surface p-4 animate-pulse">
                    <div className="h-5 bg-border/50 rounded w-1/3 mb-2" />
                    <div className="h-4 bg-border/30 rounded w-1/4" />
                  </div>
                ))}
              </>
            ) : courses.length === 0 ? (
              <div className="py-10 px-6 text-center rounded-button border border-dashed border-border bg-surface-muted/30">
                <p className="text-sm font-medium text-ink mb-1">No courses yet</p>
                <p className="text-sm text-ink-muted mb-4">
                  Upload a syllabus to extract assignments, or add a course manually.
                </p>
                <button
                  type="button"
                  onClick={() => setAdding(true)}
                  className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
                >
                  Add a course
                </button>
              </div>
            ) : (
              <>
                {recentCourses.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-ink-muted mb-2">Recently viewed</p>
                    <div className="flex flex-wrap gap-1">
                      {recentCourses.map(c => (
                        <Link
                          key={c.id}
                          to={`/app/courses/${c.id}`}
                          className="rounded-button border border-border bg-surface px-2 py-1 text-xs text-ink-muted hover:text-ink hover:bg-surface-muted no-underline"
                        >
                          {c.course_name}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
                {sortedCourses.map((c, i) => (
                <div
                  key={c.id}
                  className="animate-fade-in-up"
                  style={{ animationDelay: `${780 + i * 50}ms` }}
                >
                  <CourseCard
                    course={{
                      id: c.id,
                      course_name: c.course_name || c.name || 'Course',
                      term: '',
                      assignment_count: c.assignment_count ?? 0,
                    }}
                    onDelete={() => handleDeleteCourse(c.id)}
                  />
                </div>
              ))}
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
