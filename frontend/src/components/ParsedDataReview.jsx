/**
 * Editable table of parsed assignments. User can edit name, due, hours and confirm.
 * DISCLAIMER: Project structure may change. Functions may be added or modified.
 */
import { useState } from 'react';

/** Inline-editable cell. Toggles between display and input on click. */
function EditableCell({ value, onChange, type = 'text' }) {
  const [editing, setEditing] = useState(false);
  const [local, setLocal] = useState(value);

  /** Saves edited value and exits edit mode. */
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

/** Table of assignments with editable cells. onAssignmentsChange updates list; onConfirm saves and proceeds. */
export default function ParsedDataReview({
  courseName,
  assignments,
  onAssignmentsChange,
  onConfirm,
  saving = false,
  saveError = '',
}) {
  /** Updates one assignment field and notifies parent via onAssignmentsChange. */
  const updateAssignment = (id, field, value) => {
    onAssignmentsChange(
      assignments.map(a => (a.id === id ? { ...a, [field]: value } : a))
    );
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
        Edit any cell by clicking. Confirm when everything looks correct.
      </p>
      <div className="overflow-x-auto rounded-input border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-muted">
              <th className="text-left font-medium text-ink px-3 py-2">
                Assignment
              </th>
              <th className="text-left font-medium text-ink px-3 py-2">
                Due date
              </th>
              <th className="text-left font-medium text-ink px-3 py-2">
                Hours
              </th>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {saveError && <p className="text-sm text-red-500">{saveError}</p>}
      <div className="flex justify-end">
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
