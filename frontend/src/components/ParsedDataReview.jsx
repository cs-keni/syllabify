/**
 * Editable table of parsed assignments and assessments (exams, projects, etc.).
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

/** Table of assignments with editable cells, type column, and add/delete. */
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

  const addRow = () => {
    const newId = `temp-${Date.now()}`;
    onAssignmentsChange([
      ...assignments,
      { id: newId, name: '', due: '', hours: 3, type: 'assignment' },
    ]);
  };

  const deleteRow = (id) => {
    onAssignmentsChange(assignments.filter(a => a.id !== id));
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium text-ink">{courseName}</h2>
      {saveError && (
        <div className="rounded-input bg-red-500/10 border border-red-500/30 px-3 py-2 text-sm text-red-600">
          {saveError}
        </div>
      )}
      <p className="text-sm text-ink-muted">
        Edit any cell by clicking. Add or remove rows as needed, then confirm.
      </p>
      <div className="overflow-x-auto rounded-input border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-muted">
              <th className="text-left font-medium text-ink px-3 py-2">
                Title
              </th>
              <th className="text-left font-medium text-ink px-3 py-2">
                Type
              </th>
              <th className="text-left font-medium text-ink px-3 py-2">
                Due date
              </th>
              <th className="text-left font-medium text-ink px-3 py-2">
                Hours
              </th>
              <th className="w-10 px-2 py-2" aria-label="Remove row" />
            </tr>
          </thead>
          <tbody>
            {assignments.map((a, i) => (
              <tr
                key={a.id}
                className="border-b border-border-subtle animate-fade-in-up"
                style={{ animationDelay: `${i * 80}ms` }}
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
                    onChange={e =>
                      updateAssignment(a.id, 'type', e.target.value)
                    }
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
                    value={a.due}
                    onChange={v => updateAssignment(a.id, 'due', v)}
                    type="date"
                  />
                </td>
                <td className="px-3 py-2">
                  <EditableCell
                    value={String(a.hours)}
                    onChange={v =>
                      updateAssignment(a.id, 'hours', Number(v) || 0)
                    }
                    type="number"
                  />
                </td>
                <td className="px-2 py-2">
                  <button
                    type="button"
                    onClick={() => deleteRow(a.id)}
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
      <div className="flex flex-wrap items-center justify-end gap-3">
        <button
          type="button"
          onClick={addRow}
          className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-muted hover:text-ink transition-colors duration-200"
        >
          + Add assignment
        </button>
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
