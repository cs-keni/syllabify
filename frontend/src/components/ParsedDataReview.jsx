/**
 * Editable table of parsed assignments and assessments, organized by section.
 * Sections: Exams, Projects, Assignments, Quizzes, Participation, Other.
 * User can edit name, type, due, hours; add or delete rows; then confirm.
 */
import { useState } from 'react';

const ASSESSMENT_TYPES = [
  { value: 'assignment', label: 'Assignment' },
  { value: 'midterm', label: 'Midterm' },
  { value: 'final', label: 'Final' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'project', label: 'Project' },
  { value: 'participation', label: 'Participation' },
];

/** Map assignment type -> section for grouping. */
const TYPE_TO_SECTION = {
  midterm: 'exams',
  final: 'exams',
  project: 'projects',
  assignment: 'assignments',
  quiz: 'quizzes',
  participation: 'participation',
};
const SECTION_ORDER = ['exams', 'projects', 'assignments', 'quizzes', 'participation', 'other'];
const SECTION_LABELS = {
  exams: 'Exams (midterms & finals)',
  projects: 'Projects',
  assignments: 'Assignments',
  quizzes: 'Quizzes',
  participation: 'Participation',
  other: 'Other',
};

/** Inline-editable cell. Toggles between display and input on click. */
function EditableCell({ value, onChange, type = 'text' }) {
  const [editing, setEditing] = useState(false);
  const [local, setLocal] = useState(value);

  const save = () => {
    onChange(local);
    setEditing(false);
  };

  if (editing) {
    return (
      <input
        type={type}
        value={local}
        onChange={e => setLocal(e.target.value)}
        onBlur={save}
        onKeyDown={e => e.key === 'Enter' && save()}
        autoFocus
        className="w-full rounded min-w-0 border border-accent bg-surface px-2 py-1 text-sm text-ink focus:outline-none"
      />
    );
  }
  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className="w-full text-left px-2 py-1 rounded hover:bg-surface-muted text-sm text-ink"
    >
      {value}
    </button>
  );
}

/** Group assignments by section. */
function groupBySection(assignments) {
  const groups = { exams: [], projects: [], assignments: [], quizzes: [], participation: [], other: [] };
  for (const a of assignments) {
    const t = (a.type || 'assignment').toLowerCase();
    const section = TYPE_TO_SECTION[t] || 'other';
    groups[section].push(a);
  }
  return groups;
}

/** Single section table. */
function SectionTable({ label, items, onUpdate, onDelete }) {
  const updateAssignment = (id, field, value) => {
    onUpdate(id, field, value);
  };

  if (items.length === 0) return null;

  return (
    <div className="mb-6">
      <h3 className="text-sm font-semibold text-ink-muted uppercase tracking-wider mb-2 px-1">
        {label}
      </h3>
      <div className="overflow-x-auto rounded-input border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-muted">
              <th className="text-left font-medium text-ink px-3 py-2">Title</th>
              <th className="text-left font-medium text-ink px-3 py-2">Type</th>
              <th className="text-left font-medium text-ink px-3 py-2">Due date</th>
              <th className="text-left font-medium text-ink px-3 py-2">Hours</th>
              <th className="w-10 px-2 py-2" aria-label="Remove row" />
            </tr>
          </thead>
          <tbody>
            {items.map((a, i) => (
              <tr
                key={a.id}
                className="border-b border-border-subtle animate-fade-in-up"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <td className="px-3 py-2">
                  <EditableCell
                    value={a.name}
                    onChange={v => updateAssignment(a.id, 'name', v)}
                  />
                </td>
                <td className="px-3 py-2">
                  <select
                    value={a.type || 'assignment'}
                    onChange={e => updateAssignment(a.id, 'type', e.target.value)}
                    className="w-full rounded border border-border bg-surface px-2 py-1 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
                  >
                    {ASSESSMENT_TYPES.map(({ value, label }) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <EditableCell
                    value={a.due || a.due_date || ''}
                    onChange={v => updateAssignment(a.id, 'due', v)}
                    type="date"
                  />
                </td>
                <td className="px-3 py-2">
                  <EditableCell
                    value={String(a.hours)}
                    onChange={v => updateAssignment(a.id, 'hours', Number(v) || 0)}
                    type="number"
                  />
                </td>
                <td className="px-2 py-2">
                  <button
                    type="button"
                    onClick={() => onDelete(a.id)}
                    className="rounded-button p-1.5 text-ink-muted hover:bg-red-500/10 hover:text-red-600 transition-colors"
                    title="Remove row"
                    aria-label="Remove row"
                  >
                    <span aria-hidden>×</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Editable review with sections. */
export default function ParsedDataReview({
  courseName,
  assignments,
  onAssignmentsChange,
  onConfirm,
  saving = false,
  saveError = '',
}) {
  const updateAssignment = (id, field, value) => {
    onAssignmentsChange(
      assignments.map(a => (a.id === id ? { ...a, [field]: value } : a))
    );
  };

  const addRow = (defaultType = 'assignment') => {
    const newId = `temp-${Date.now()}`;
    onAssignmentsChange([
      ...assignments,
      { id: newId, name: '', due: '', hours: 3, type: defaultType },
    ]);
  };

  const deleteRow = (id) => {
    onAssignmentsChange(assignments.filter(a => a.id !== id));
  };

  const groups = groupBySection(assignments);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium text-ink">{courseName}</h2>
      {saveError && (
        <div className="rounded-input bg-red-500/10 border border-red-500/30 px-3 py-2 text-sm text-red-600">
          {saveError}
        </div>
      )}
      <p className="text-sm text-ink-muted">
        Review parsed data by section. Edit any cell by clicking, remove duplicates or bad entries,
        add new ones, then confirm.
      </p>
      {SECTION_ORDER.map(section => (
        <SectionTable
          key={section}
          label={SECTION_LABELS[section]}
          items={groups[section]}
          onUpdate={updateAssignment}
          onDelete={deleteRow}
        />
      ))}
      <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => addRow('assignment')}
            className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-muted hover:text-ink transition-colors duration-200"
          >
            + Add assignment
          </button>
          <button
            type="button"
            onClick={() => addRow('midterm')}
            className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-muted hover:text-ink transition-colors duration-200"
          >
            + Add exam
          </button>
        </div>
        <button
          type="button"
          onClick={onConfirm}
          disabled={saving}
          className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50 transition-colors duration-200"
        >
          {saving ? 'Saving…' : 'Confirm and continue'}
        </button>
      </div>
    </div>
  );
}
