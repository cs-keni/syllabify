import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  getCourse,
  deleteCourse,
  addAssignments,
  updateAssignment,
  deleteAssignment,
  parseSyllabus,
} from '../api/client';
import toast from 'react-hot-toast';

const ASSIGNMENT_TYPES = [
  { value: 'assignment', label: 'Assignment' },
  { value: 'midterm', label: 'Midterm' },
  { value: 'final', label: 'Final' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'project', label: 'Project' },
  { value: 'participation', label: 'Participation' },
];

function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function toInputDate(d) {
  if (!d) return '';
  const x = new Date(d);
  return x.toISOString().slice(0, 10);
}

function getDatePresets() {
  const today = new Date();
  const toYMD = d => d.toISOString().slice(0, 10);
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  const nextMonday = () => {
    const d = new Date(today);
    const day = d.getDay();
    d.setDate(d.getDate() + (day === 0 ? 1 : 8 - day));
    return d;
  };
  return [
    { label: 'Today', value: toYMD(today) },
    { label: 'Tomorrow', value: toYMD(addDays(today, 1)) },
    { label: 'Next Mon', value: toYMD(nextMonday()) },
    { label: '+1 wk', value: toYMD(addDays(today, 7)) },
    { label: '+2 wks', value: toYMD(addDays(today, 14)) },
  ];
}

function AssignmentRow({ assignment, courseId, allAssignments, token, onUpdated, onRemoved }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(assignment.assignment_name);
  const [due, setDue] = useState(toInputDate(assignment.due_date));
  const [hours, setHours] = useState(((assignment.work_load || 0) / 4).toFixed(1));
  const [type, setType] = useState(assignment.assignment_type || 'assignment');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateAssignment(token, assignment.id, {
        assignment_name: name.trim(),
        due_date: due || null,
        hours: parseFloat(hours) || 3,
        type,
      });
      toast.success('Updated');
      setEditing(false);
      onUpdated?.();
    } catch (e) {
      toast.error(e.message || 'Failed to update');
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicate = async () => {
    if (!courseId) return;
    setSaving(true);
    try {
      await addAssignments(courseId, [{
        name: (assignment.assignment_name || '') + ' (copy)',
        due: assignment.due_date || null,
        hours: (assignment.work_load || 0) / 4,
        type: assignment.assignment_type || 'assignment',
      }]);
      toast.success('Assignment duplicated');
      onUpdated?.();
    } catch (e) {
      toast.error(e.message || 'Failed to duplicate');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Remove this assignment?')) return;
    setDeleting(true);
    try {
      await deleteAssignment(token, assignment.id);
      toast.success('Removed');
      onRemoved?.();
    } catch (e) {
      toast.error(e.message || 'Failed to remove');
    } finally {
      setDeleting(false);
    }
  };

  if (editing) {
    return (
      <li className="flex flex-wrap items-center gap-2 px-3 py-2 rounded-button border border-accent bg-accent-muted/30 text-sm">
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="Name"
          className="flex-1 min-w-[120px] rounded-input border border-border bg-surface px-2 py-1 text-sm"
        />
        <div>
          <div className="flex items-center gap-1">
            <input
              type="date"
              value={due}
              onChange={e => setDue(e.target.value)}
              className="rounded-input border border-border bg-surface px-2 py-1 text-sm"
            />
            {getDatePresets().slice(0, 3).map(p => (
              <button
                key={p.label}
                type="button"
                onClick={() => setDue(p.value)}
                className="rounded-button border border-border px-1 py-0.5 text-xs text-ink-muted hover:text-ink"
              >
                {p.label}
              </button>
            ))}
          </div>
          {due && (allAssignments || []).filter(a => a.id !== assignment.id).some(a => a.due_date && String(a.due_date).slice(0, 10) === due) && (
            <p className="text-xs text-amber-600 mt-0.5">Same date as another assignment</p>
          )}
        </div>
        <input
          type="number"
          min="0.5"
          step="0.5"
          value={hours}
          onChange={e => setHours(e.target.value)}
          className="w-16 rounded-input border border-border bg-surface px-2 py-1 text-sm"
        />
        <select
          value={type}
          onChange={e => setType(e.target.value)}
          className="rounded-input border border-border bg-surface px-2 py-1 text-sm"
        >
          {ASSIGNMENT_TYPES.map(t => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="rounded-button bg-accent px-2 py-1 text-xs text-white hover:bg-accent-hover disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          className="rounded-button border border-border px-2 py-1 text-xs text-ink-muted hover:text-ink"
        >
          Cancel
        </button>
      </li>
    );
  }

  const isOverdue = assignment.due_date && new Date(assignment.due_date) < new Date(new Date().toDateString());
  return (
    <li className={`flex items-center justify-between px-3 py-2 rounded-button border text-sm group ${isOverdue ? 'border-red-300 bg-red-50/50 dark:border-red-800 dark:bg-red-950/30' : 'border-border-subtle bg-surface'}`}>
      <span className={`font-medium ${isOverdue ? 'text-red-600 dark:text-red-400' : 'text-ink'}`}>
        {assignment.assignment_name}
        {isOverdue && <span className="ml-2 text-xs font-normal text-red-500">Overdue</span>}
      </span>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-ink-muted">
          {formatDate(assignment.due_date)} · {((assignment.work_load || 0) / 4).toFixed(1)}h
        </span>
        <button
          type="button"
          onClick={handleDuplicate}
          disabled={saving}
          className="opacity-0 group-hover:opacity-100 rounded-button border border-border px-2 py-0.5 text-xs text-ink-muted hover:text-ink disabled:opacity-50 transition-opacity"
          title="Duplicate"
        >
          Copy
        </button>
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="opacity-0 group-hover:opacity-100 rounded-button border border-border px-2 py-0.5 text-xs text-ink-muted hover:text-ink transition-opacity"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="opacity-0 group-hover:opacity-100 rounded-button border border-red-200 px-2 py-0.5 text-xs text-red-500 hover:bg-red-50 disabled:opacity-50 transition-opacity"
        >
          {deleting ? '…' : 'Remove'}
        </button>
      </div>
    </li>
  );
}

export default function Course() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const refreshCourse = () =>
    getCourse(courseId)
      .then(data => setCourse(data))
      .catch(e => setError(e.message));

  useEffect(() => {
    refreshCourse().finally(() => setLoading(false));
  }, [courseId]);

  useEffect(() => {
    if (!course) return;
    try {
      const key = 'syllabify_recent_courses';
      const stored = JSON.parse(localStorage.getItem(key) || '[]');
      const entry = { id: course.id, course_name: course.course_name, term_name: course.term_name };
      const filtered = stored.filter(c => c.id !== course.id);
      const next = [entry, ...filtered].slice(0, 5);
      localStorage.setItem(key, JSON.stringify(next));
    } catch (_) {}
  }, [course]);

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
      <div className="space-y-8 animate-fade-in">
        <div>
          <div className="h-4 bg-border/40 rounded w-48 mb-3" />
          <div className="h-8 bg-border/50 rounded w-64 mb-2" />
          <div className="h-4 bg-border/30 rounded w-32" />
        </div>
        <div className="rounded-card border border-border bg-surface p-6 space-y-3">
          <div className="h-4 bg-border/40 rounded w-24 mb-4" />
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-12 bg-border/20 rounded" />
          ))}
        </div>
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
      <CourseHeader
        course={course}
        navigate={navigate}
        confirmDelete={confirmDelete}
        setConfirmDelete={setConfirmDelete}
        deleting={deleting}
        handleDelete={handleDelete}
      />
      <AssignmentsSection
        course={course}
        token={token}
        refreshCourse={refreshCourse}
        navigate={navigate}
      />
      <AddAssignmentForm courseId={courseId} courseAssignments={course.assignments} token={token} onAdded={refreshCourse} />
      <PasteParseSection courseId={courseId} token={token} onAdded={refreshCourse} />
    </div>
  );
}

function CourseHeader({
  course,
  navigate,
  confirmDelete,
  setConfirmDelete,
  deleting,
  handleDelete,
}) {
  return (
    <div className="sticky top-14 z-10 -mx-4 -mt-6 px-4 pt-6 pb-4 -mb-4 bg-surface border-b border-border flex items-start justify-between gap-4">
      <div>
        <nav className="flex items-center gap-1.5 text-sm text-ink-muted" aria-label="Breadcrumb">
          <Link to="/app" className="hover:text-ink transition-colors no-underline">
            Dashboard
          </Link>
          <span aria-hidden>/</span>
          <span className="text-ink">{course.term_name || 'Term'}</span>
          <span aria-hidden>/</span>
          <span className="text-ink font-medium">{course.course_name}</span>
        </nav>
        <h1 className="mt-2 text-2xl font-semibold text-ink">{course.course_name}</h1>
        <p className="mt-1 text-sm text-ink-muted">{course.term_name}</p>
      </div>

      <div className="flex gap-2 shrink-0">
        <button
          type="button"
          onClick={() =>
            navigate('/app/upload', {
              state: { courseId: course.id, courseName: course.course_name },
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
  );
}

function AssignmentsSection({ course, token, refreshCourse, navigate }) {
  const [sortBy, setSortBy] = useState('due');
  const assignments = [...(course.assignments || [])].sort((a, b) => {
    if (sortBy === 'name') return (a.assignment_name || '').localeCompare(b.assignment_name || '');
    const ad = a.due_date ? new Date(a.due_date) : new Date(0);
    const bd = b.due_date ? new Date(b.due_date) : new Date(0);
    return sortBy === 'due-desc' ? bd - ad : ad - bd;
  });
  return (
    <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-ink">
          Assignments
          <span className="ml-2 text-xs font-normal text-ink-subtle bg-surface-muted rounded-button px-2 py-0.5">
            {course.assignments?.length ?? 0}
          </span>
        </h2>
        <div className="flex items-center gap-2">
          <label htmlFor="sort-assignments" className="text-xs text-ink-muted">Sort:</label>
          <select
            id="sort-assignments"
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="rounded-input border border-border bg-surface px-2 py-1 text-xs"
          >
            <option value="due">Due date</option>
            <option value="due-desc">Due (latest first)</option>
            <option value="name">Name</option>
          </select>
          <button
            type="button"
            onClick={() =>
              navigate('/app/upload', {
                state: { courseId: course.id, courseName: course.course_name },
              })
            }
            className="text-sm font-medium text-accent hover:text-accent-hover transition-colors"
          >
            + Upload syllabus
          </button>
        </div>
      </div>

      {!course.assignments?.length ? (
        <div className="py-10 px-6 text-center rounded-button border border-dashed border-border bg-surface-muted/30">
          <p className="text-sm font-medium text-ink mb-1">No assignments yet</p>
          <p className="text-sm text-ink-muted mb-4">Upload a syllabus to extract them, or add one manually below.</p>
          <button
            type="button"
            onClick={() =>
              navigate('/app/upload', {
                state: { courseId: course.id, courseName: course.course_name },
              })
            }
            className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
          >
            Upload syllabus
          </button>
        </div>
      ) : (
        <ul className="space-y-2">
          {assignments.map(a => (
            <AssignmentRow
              key={a.id}
              assignment={a}
              courseId={course.id}
              allAssignments={course.assignments}
              token={token}
              onUpdated={refreshCourse}
              onRemoved={refreshCourse}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function AddAssignmentForm({ courseId, courseAssignments, token, onAdded }) {
  const [expanded, setExpanded] = useState(false);
  const [name, setName] = useState('');
  const [due, setDue] = useState('');
  const [hours, setHours] = useState('3');
  const [type, setType] = useState('assignment');
  const [adding, setAdding] = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();
    if (!name.trim()) return;
    setAdding(true);
    try {
      await addAssignments(courseId, [
        {
          name: name.trim(),
          due: due || null,
          hours: parseFloat(hours) || 3,
          type,
        },
      ]);
      toast.success('Assignment added');
      setName('');
      setDue('');
      setHours('3');
      setType('assignment');
      setExpanded(false);
      onAdded?.();
    } catch (e) {
      toast.error(e.message || 'Failed to add');
    } finally {
      setAdding(false);
    }
  };

  return (
    <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="text-sm font-medium text-ink hover:text-accent transition-colors"
      >
        {expanded ? '−' : '+'} Add assignment manually
      </button>
      {expanded && (
        <form onSubmit={handleSubmit} className="mt-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs text-ink-muted mb-0.5">Name *</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Homework 3"
              required
              className="rounded-input border border-border bg-surface px-3 py-2 text-sm w-40"
            />
          </div>
          <div>
            <label className="block text-xs text-ink-muted mb-0.5">Due date</label>
            <input
              type="date"
              value={due}
              onChange={e => setDue(e.target.value)}
              className="rounded-input border border-border bg-surface px-3 py-2 text-sm mb-1"
            />
            <div className="flex flex-wrap gap-1">
              {getDatePresets().map(p => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => setDue(p.value)}
                  className="rounded-button border border-border px-1.5 py-0.5 text-xs text-ink-muted hover:text-ink hover:bg-surface-muted"
                >
                  {p.label}
                </button>
              ))}
            </div>
            {due && (courseAssignments || []).some(a => a.due_date && String(a.due_date).slice(0, 10) === due) && (
              <p className="text-xs text-amber-600 mt-1">Another assignment is due on this date.</p>
            )}
          </div>
          <div>
            <label className="block text-xs text-ink-muted mb-0.5">Hours</label>
            <input
              type="number"
              min="0.5"
              step="0.5"
              value={hours}
              onChange={e => setHours(e.target.value)}
              className="rounded-input border border-border bg-surface px-3 py-2 text-sm w-20"
            />
          </div>
          <div>
            <label className="block text-xs text-ink-muted mb-0.5">Type</label>
            <select
              value={type}
              onChange={e => setType(e.target.value)}
              className="rounded-input border border-border bg-surface px-3 py-2 text-sm"
            >
              {ASSIGNMENT_TYPES.map(t => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={adding || !name.trim()}
            className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-60"
          >
            {adding ? 'Adding…' : 'Add'}
          </button>
        </form>
      )}
    </section>
  );
}

function PasteParseSection({ courseId, token, onAdded }) {
  const [expanded, setExpanded] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState(null);
  const [parseError, setParseError] = useState('');
  const [selected, setSelected] = useState({});
  const [edits, setEdits] = useState({});
  const [adding, setAdding] = useState(false);

  const handleParse = async () => {
    if (!pasteText.trim()) return;
    setParsing(true);
    setParseError('');
    setParsed(null);
    try {
      const res = await parseSyllabus(token, { text: pasteText.trim() });
      const items = res.assignments || [];
      setParsed(items);
      setSelected(Object.fromEntries(items.map((a, i) => [i, true])));
      setEdits({});
    } catch (e) {
      setParseError(e.message || 'Parse failed');
    } finally {
      setParsing(false);
    }
  };

  const toggleSelect = i => setSelected(s => ({ ...s, [i]: !s[i] }));
  const updateEdit = (i, field, value) =>
    setEdits(e => ({ ...e, [i]: { ...(e[i] || {}), [field]: value } }));

  const getItem = (item, i) => {
    const ed = edits[i] || {};
    return {
      name: ed.name ?? item.name ?? 'Untitled',
      due: ed.due ?? item.due ?? item.due_date ?? null,
      hours: ed.hours ?? item.hours ?? 3,
      type: ed.type ?? item.type ?? 'assignment',
    };
  };

  const handleAddSelected = async () => {
    if (!parsed?.length) return;
    const items = Object.keys(selected)
      .filter(i => selected[i])
      .map(i => getItem(parsed[i], parseInt(i, 10)))
      .map(a => ({ name: a.name, due: a.due || a.due_date || null, hours: a.hours ?? 3, type: a.type }));
    if (items.length === 0) {
      toast.error('Select at least one assignment');
      return;
    }
    setAdding(true);
    try {
      await addAssignments(courseId, items);
      toast.success(`Added ${items.length} assignment(s)`);
      setPasteText('');
      setParsed(null);
      setExpanded(false);
      onAdded?.();
    } catch (e) {
      toast.error(e.message || 'Failed to add');
    } finally {
      setAdding(false);
    }
  };

  const handleCancel = () => {
    setPasteText('');
    setParsed(null);
    setParseError('');
    setExpanded(false);
  };

  return (
    <section className="rounded-card bg-surface-elevated border border-border p-6 shadow-card">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="text-sm font-medium text-ink hover:text-accent transition-colors"
      >
        {expanded ? '−' : '+'} Add from pasted text
      </button>
      {expanded && (
        <div className="mt-4 space-y-4">
          <textarea
            value={pasteText}
            onChange={e => setPasteText(e.target.value)}
            placeholder="Paste assignment details (e.g. 'Homework 3 due Mar 15, 4 hours')…"
            rows={4}
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-subtle resize-y"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleParse}
              disabled={parsing || !pasteText.trim()}
              className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-60"
            >
              {parsing ? 'Parsing…' : 'Parse'}
            </button>
            {parseError && <span className="text-sm text-red-500">{parseError}</span>}
          </div>
          {parsed && parsed.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm text-ink-muted">Select assignments to add:</p>
              <ul className="space-y-1 max-h-48 overflow-auto">
                {parsed.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 py-1 text-sm">
                    <input
                      type="checkbox"
                      checked={selected[i] !== false}
                      onChange={() => toggleSelect(i)}
                      className="rounded border-border text-accent"
                    />
                    <input
                      type="text"
                      value={getItem(item, i).name}
                      onChange={e => updateEdit(i, 'name', e.target.value)}
                      className="flex-1 rounded-input border border-border bg-surface px-2 py-0.5 text-sm"
                    />
                    <input
                      type="date"
                      value={toInputDate(getItem(item, i).due)}
                      onChange={e => updateEdit(i, 'due', e.target.value)}
                      className="rounded-input border border-border bg-surface px-2 py-0.5 text-sm w-32"
                    />
                    <input
                      type="number"
                      min="0.5"
                      step="0.5"
                      value={getItem(item, i).hours}
                      onChange={e => updateEdit(i, 'hours', parseFloat(e.target.value) || 0)}
                      className="rounded-input border border-border bg-surface px-2 py-0.5 text-sm w-16"
                    />
                    <select
                      value={getItem(item, i).type}
                      onChange={e => updateEdit(i, 'type', e.target.value)}
                      className="rounded-input border border-border bg-surface px-2 py-0.5 text-sm"
                    >
                      {ASSIGNMENT_TYPES.map(t => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </li>
                ))}
              </ul>
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={handleAddSelected}
                  disabled={adding}
                  className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-60"
                >
                  {adding ? 'Adding…' : 'Add selected'}
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="rounded-button border border-border px-4 py-2 text-sm text-ink-muted hover:text-ink"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
