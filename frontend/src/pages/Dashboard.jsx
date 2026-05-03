/**
 * Dashboard: weekly overview, upcoming assignments, course cards.
 */
import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  getCourses,
  createCourse,
  deleteCourse,
  getUpcomingAssignments,
} from '../api/client';
import CourseCard from '../components/CourseCard';
import TermSelector from '../components/TermSelector';
import OnboardingTooltip from '../components/OnboardingTooltip';

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

/** Main dashboard. Shows courses and links to schedule. */
export default function Dashboard() {
  const { user, token } = useAuth();
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
  const [pendingDelete, setPendingDelete] = useState(null); // { id, name, assignmentCount }
  const [upcomingAssignments, setUpcomingAssignments] = useState([]);

  useEffect(() => {
    try {
      const stored = JSON.parse(
        localStorage.getItem('syllabify_recent_courses') || '[]'
      );
      const courseIds = new Set(courses.map(c => c.id));
      const valid = stored
        .filter(
          c => c.id && c.course_name && (!currentTermId || courseIds.has(c.id))
        )
        .slice(0, 5);
      setRecentCourses(valid);
    } catch (_) {
      setRecentCourses([]);
    }
  }, [courses, currentTermId]);

  const sortedCourses = [...courses].sort((a, b) => {
    if (sortBy === 'name')
      return (a.course_name || '').localeCompare(b.course_name || '');
    const ac = a.assignment_count ?? 0;
    const bc = b.assignment_count ?? 0;
    return sortBy === 'count-desc' ? bc - ac : ac - bc;
  });

  // Courses load when term changes (via handleTermChange from TermSelector)

  const handleDeleteCourse = async () => {
    if (!token || !pendingDelete) return;
    const { id } = pendingDelete;
    setPendingDelete(null);
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
    setUpcomingAssignments([]);
    if (!termId) return;
    setLoadingCourses(true);
    try {
      const [coursesData, upcomingData] = await Promise.all([
        getCourses(termId),
        token
          ? getUpcomingAssignments(token, termId, 5).catch(() => ({
              assignments: [],
            }))
          : Promise.resolve({ assignments: [] }),
      ]);
      setCourses(coursesData.courses || []);
      setUpcomingAssignments(upcomingData.assignments || []);
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
    const exists = courses.some(
      c => (c.course_name || '').toLowerCase() === name.toLowerCase()
    );
    if (exists) {
      setCourseError('A course with this name already exists.');
      return;
    }
    setSaving(true);
    setCourseError('');
    try {
      const course = await createCourse(currentTermId, name);
      setCourses(prev => [...prev, course]);
      setNewCourseName('');
      setAdding(false);
    } catch (e) {
      setCourseError(e.message || 'Could not add course');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 sm:space-y-10">
      <OnboardingTooltip />
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

      <div className="grid gap-8 lg:grid-cols-2">
        <section className="rounded-card bg-surface-elevated border border-border p-4 sm:p-6 shadow-card animate-fade-in-up [animation-delay:200ms]">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
            <h2 className="text-sm font-medium text-ink">Upcoming deadlines</h2>
            <Link
              to="/app/schedule"
              className="text-sm font-medium text-accent no-underline hover:text-accent-hover transition-colors duration-200"
            >
              View schedule →
            </Link>
          </div>
          {!currentTermId ? (
            <p className="text-sm text-ink-muted py-2">
              Select a term to see upcoming deadlines.
            </p>
          ) : upcomingAssignments.length === 0 ? (
            <p className="text-sm text-ink-muted py-2">
              No upcoming deadlines — all clear!
            </p>
          ) : (
            <ul className="space-y-2">
              {upcomingAssignments.map(a => {
                const due = a.due_date ? new Date(a.due_date) : null;
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                const daysLeft = due
                  ? Math.ceil((due - today) / 86400000)
                  : null;
                return (
                  <li key={a.id} className="flex items-center gap-3 text-sm">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: a.color || '#6b7280' }}
                    />
                    <Link
                      to={`/app/courses/${a.course_id}`}
                      className="truncate text-ink no-underline hover:text-accent transition-colors flex-1"
                    >
                      {a.assignment_name}
                      <span className="ml-1 text-xs text-ink-muted">
                        · {a.course_name}
                      </span>
                    </Link>
                    {daysLeft !== null && (
                      <span
                        className={`shrink-0 text-xs tabular-nums ${daysLeft <= 2 ? 'text-red-500 font-medium' : daysLeft <= 7 ? 'text-amber-500' : 'text-ink-muted'}`}
                      >
                        {daysLeft === 0
                          ? 'today'
                          : daysLeft === 1
                            ? '1 day'
                            : `${daysLeft} days`}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* Courses section */}
        <section className="rounded-card bg-surface-elevated border border-border p-4 sm:p-6 shadow-card animate-fade-in-up [animation-delay:700ms]">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <h2 className="text-sm font-medium text-ink">Courses</h2>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <label htmlFor="sort-courses" className="text-xs text-ink-muted">
                Sort:
              </label>
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
                <p className="text-sm text-ink-muted mb-2">
                  Select a term above to view its courses.
                </p>
                <p className="text-xs text-ink-subtle">
                  Choose an existing term or create a new one.
                </p>
              </div>
            ) : loadingCourses ? (
              <>
                {[1, 2, 3].map(i => (
                  <div
                    key={i}
                    className="rounded-card border border-border bg-surface p-4 animate-pulse"
                  >
                    <div className="h-5 bg-border/50 rounded w-1/3 mb-2" />
                    <div className="h-4 bg-border/30 rounded w-1/4" />
                  </div>
                ))}
              </>
            ) : courses.length === 0 ? (
              <div className="py-10 px-6 text-center rounded-button border border-dashed border-border bg-surface-muted/30">
                <p className="text-sm font-medium text-ink mb-1">
                  No courses yet
                </p>
                <p className="text-sm text-ink-muted mb-4">
                  Upload a syllabus to extract assignments, or add a course
                  manually.
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
                    <p className="text-xs text-ink-muted mb-2">
                      Recently viewed
                    </p>
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
                      onDelete={() =>
                        setPendingDelete({
                          id: c.id,
                          name: c.course_name || c.name || 'Course',
                          assignmentCount: c.assignment_count ?? 0,
                        })
                      }
                    />
                  </div>
                ))}
              </>
            )}
          </div>
        </section>
      </div>

      {pendingDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setPendingDelete(null)}
          />
          <div className="relative z-10 w-full max-w-sm rounded-xl border border-border bg-surface-elevated p-5 shadow-xl animate-fade-in-up">
            <h3 className="text-base font-semibold text-ink">Delete course?</h3>
            <p className="mt-2 text-sm text-ink-muted">
              Delete{' '}
              <span className="font-medium text-ink">{pendingDelete.name}</span>{' '}
              and its{' '}
              <span className="font-medium text-ink">
                {pendingDelete.assignmentCount}
              </span>{' '}
              {pendingDelete.assignmentCount === 1
                ? 'assignment'
                : 'assignments'}
              ? This can&apos;t be undone.
            </p>
            <div className="mt-4 flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => setPendingDelete(null)}
                className="rounded-button border border-border px-3 py-1.5 text-sm text-ink-muted hover:text-ink"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteCourse}
                className="rounded-button bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
