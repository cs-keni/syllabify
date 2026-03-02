/**
 * Review parsed syllabus in sections: Meeting times, Exams, Projects, Assignments, etc.
 * Each section: add (modal form), delete per row, drag-and-drop to reorder or move between sections.
 */
import { useState } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const ASSESSMENT_TYPES = [
  { value: 'assignment', label: 'Assignment' },
  { value: 'midterm', label: 'Midterm' },
  { value: 'final', label: 'Final' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'project', label: 'Project' },
  { value: 'participation', label: 'Participation' },
];

const TYPE_TO_SECTION = {
  midterm: 'exams',
  final: 'exams',
  project: 'projects',
  assignment: 'assignments',
  quiz: 'quizzes',
  participation: 'participation',
};
const SECTION_ORDER = [
  'exams',
  'projects',
  'assignments',
  'quizzes',
  'participation',
  'other',
];
const SECTION_LABELS = {
  exams: 'Exams (midterms & finals)',
  projects: 'Projects',
  assignments: 'Assignments',
  quizzes: 'Quizzes',
  participation: 'Participation',
  other: 'Other',
};

const DAYS = [
  { value: 'MO', label: 'Monday' },
  { value: 'TU', label: 'Tuesday' },
  { value: 'WE', label: 'Wednesday' },
  { value: 'TH', label: 'Thursday' },
  { value: 'FR', label: 'Friday' },
  { value: 'SA', label: 'Saturday' },
  { value: 'SU', label: 'Sunday' },
];

const MEETING_TYPES = [
  { value: 'lecture', label: 'Lecture' },
  { value: 'lab', label: 'Lab' },
  { value: 'discussion', label: 'Discussion' },
  { value: 'office_hours', label: 'Office hours (instructor)' },
  { value: 'ta_office_hours', label: 'Office hours (TA)' },
  { value: 'other', label: 'Other' },
];

function groupBySection(assignments) {
  const groups = {
    exams: [],
    projects: [],
    assignments: [],
    quizzes: [],
    participation: [],
    other: [],
  };
  for (const a of assignments) {
    const t = (a.type || 'assignment').toLowerCase();
    const section = TYPE_TO_SECTION[t] || 'other';
    groups[section].push(a);
  }
  return groups;
}

/** Inline-editable cell. */
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
      {value || '—'}
    </button>
  );
}

/** Generic modal backdrop + panel. */
function Modal({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="rounded-card bg-surface-elevated border border-border shadow-card max-w-md w-full max-h-[90vh] overflow-y-auto animate-fade-in-up"
        onClick={e => e.stopPropagation()}
      >
        <h3
          id="modal-title"
          className="text-lg font-medium text-ink px-4 pt-4 pb-2"
        >
          {title}
        </h3>
        <div className="px-4 pb-4">{children}</div>
      </div>
    </div>
  );
}

/** Form to add a new meeting time. */
function AddMeetingModal({ open, onClose, onAdd }) {
  const [day, setDay] = useState('MO');
  const [startTime, setStartTime] = useState('10:00');
  const [endTime, setEndTime] = useState('11:00');
  const [location, setLocation] = useState('');
  const [meetingType, setMeetingType] = useState('lecture');

  const handleSubmit = e => {
    e.preventDefault();
    onAdd({
      id: `mt-${Date.now()}`,
      day_of_week: day,
      start_time: startTime,
      end_time: endTime,
      location: location.trim() || null,
      type: meetingType,
    });
    onClose();
    setDay('MO');
    setStartTime('10:00');
    setEndTime('11:00');
    setLocation('');
    setMeetingType('lecture');
  };

  return (
    <Modal open={open} onClose={onClose} title="Add meeting time">
      <form onSubmit={handleSubmit} className="space-y-3">
        <label className="block text-sm font-medium text-ink-muted">Day</label>
        <select
          value={day}
          onChange={e => setDay(e.target.value)}
          className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
        >
          {DAYS.map(d => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-sm font-medium text-ink-muted">
              Start
            </label>
            <input
              type="time"
              value={startTime}
              onChange={e => setStartTime(e.target.value)}
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-ink-muted">
              End
            </label>
            <input
              type="time"
              value={endTime}
              onChange={e => setEndTime(e.target.value)}
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-ink-muted">
            Location (optional)
          </label>
          <input
            type="text"
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="e.g. 180 PLC"
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-ink-muted">
            Type
          </label>
          <select
            value={meetingType}
            onChange={e => setMeetingType(e.target.value)}
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            {MEETING_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-muted"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
          >
            Add
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** Form to add an instructor or TA. */
function AddInstructorModal({ open, onClose, onAdd }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');

  const handleSubmit = e => {
    e.preventDefault();
    onAdd({
      id: `inst-${Date.now()}`,
      name: name.trim() || 'Instructor',
      email: email.trim() || null,
    });
    onClose();
    setName('');
    setEmail('');
  };

  return (
    <Modal open={open} onClose={onClose} title="Add instructor or TA">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-ink-muted">
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. Jane Smith"
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-ink-muted">
            Email (optional)
          </label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="e.g. jane@university.edu"
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-muted"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
          >
            Add
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** Form to add a new assessment. */
function AddAssessmentModal({
  open,
  onClose,
  onAdd,
  defaultType = 'assignment',
}) {
  const [name, setName] = useState('');
  const [type, setType] = useState(defaultType);
  const [due, setDue] = useState('');
  const [hours, setHours] = useState(
    type === 'midterm' || type === 'final' ? 2 : type === 'quiz' ? 1 : 3
  );

  const handleSubmit = e => {
    e.preventDefault();
    onAdd({
      id: `temp-${Date.now()}`,
      name: name.trim() || 'Untitled',
      due: due.trim() || '',
      hours: Number(hours) || 1,
      type,
    });
    onClose();
    setName('');
    setType('assignment');
    setDue('');
    setHours(3);
  };

  return (
    <Modal open={open} onClose={onClose} title="Add assessment">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-ink-muted">
            Title
          </label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. Homework 1"
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-ink-muted">
            Type
          </label>
          <select
            value={type}
            onChange={e => {
              const t = e.target.value;
              setType(t);
              if (t === 'midterm' || t === 'final') setHours(2);
              else if (t === 'quiz') setHours(1);
              else if (t === 'project') setHours(4);
              else setHours(3);
            }}
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            {ASSESSMENT_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-ink-muted">
            Due date (optional)
          </label>
          <input
            type="date"
            value={due}
            onChange={e => setDue(e.target.value)}
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-ink-muted">
            Estimated hours
          </label>
          <input
            type="number"
            min={1}
            max={20}
            value={hours}
            onChange={e => setHours(Number(e.target.value) || 1)}
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:bg-surface-muted"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
          >
            Add
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** Sortable row for meeting time. */
function SortableMeetingRow({ meeting, onUpdate, onDelete }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: meeting.id, data: { kind: 'meeting' } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <tr
      ref={setNodeRef}
      style={style}
      className={`border-b border-border-subtle ${isDragging ? 'opacity-60 bg-surface-muted' : ''}`}
    >
      <td
        className="w-8 px-2 py-2 cursor-grab active:cursor-grabbing"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
      >
        <span className="text-ink-muted select-none">⋮⋮</span>
      </td>
      <td className="px-3 py-2">
        <select
          value={meeting.day_of_week || 'MO'}
          onChange={e => onUpdate(meeting.id, 'day_of_week', e.target.value)}
          className="w-full rounded border border-border bg-surface px-2 py-1 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {DAYS.map(d => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-2">
        {meeting.start_time && meeting.end_time ? (
          <>
            <span className="text-sm text-ink">{meeting.start_time}</span>
            <span className="text-ink-muted mx-1">–</span>
            <span className="text-sm text-ink">{meeting.end_time}</span>
          </>
        ) : (
          <span className="text-sm text-ink-muted italic">TBD</span>
        )}
      </td>
      <td className="px-3 py-2">
        <EditableCell
          value={meeting.location || ''}
          onChange={v => onUpdate(meeting.id, 'location', v)}
        />
      </td>
      <td className="px-3 py-2">
        <select
          value={meeting.type || 'lecture'}
          onChange={e => onUpdate(meeting.id, 'type', e.target.value)}
          className="w-full rounded border border-border bg-surface px-2 py-1 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {MEETING_TYPES.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </td>
      <td className="w-10 px-2 py-2">
        <button
          type="button"
          onClick={() => onDelete(meeting.id)}
          className="rounded-button p-1.5 text-ink-muted hover:bg-red-500/10 hover:text-red-600"
          title="Remove"
          aria-label="Remove"
        >
          ×
        </button>
      </td>
    </tr>
  );
}

/** Sortable row for assessment. */
function SortableAssessmentRow({ item, onUpdate, onDelete, sectionId }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: item.id,
    data: { kind: 'assessment', section: sectionId },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const lowConfidence =
    typeof item.confidence === 'number' && item.confidence < 0.6;

  return (
    <tr
      ref={setNodeRef}
      style={style}
      title={
        lowConfidence ? 'Parsed with low confidence—please verify' : undefined
      }
      className={`border-b border-border-subtle ${isDragging ? 'opacity-60 bg-surface-muted' : ''} ${lowConfidence ? 'bg-amber-50 dark:bg-amber-950/30' : ''}`}
    >
      <td
        className="w-8 px-2 py-2 cursor-grab active:cursor-grabbing"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
      >
        <span className="text-ink-muted select-none">⋮⋮</span>
      </td>
      <td className="px-3 py-2">
        <EditableCell
          value={item.name}
          onChange={v => onUpdate(item.id, 'name', v)}
        />
      </td>
      <td className="px-3 py-2">
        <select
          value={item.type || 'assignment'}
          onChange={e => onUpdate(item.id, 'type', e.target.value)}
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
          value={item.due || item.due_date || ''}
          onChange={v => onUpdate(item.id, 'due', v)}
          type="date"
        />
      </td>
      <td className="px-3 py-2">
        <EditableCell
          value={String(item.hours)}
          onChange={v => onUpdate(item.id, 'hours', Number(v) || 0)}
          type="number"
        />
      </td>
      <td className="w-10 px-2 py-2">
        <button
          type="button"
          onClick={() => onDelete(item.id)}
          className="rounded-button p-1.5 text-ink-muted hover:bg-red-500/10 hover:text-red-600"
          title="Remove"
          aria-label="Remove"
        >
          ×
        </button>
      </td>
    </tr>
  );
}

/** Section box: Meeting times. */
function MeetingTimesSection({
  meetingTimes,
  onMeetingTimesChange,
  onOpenAddModal,
}) {
  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: 'section-meetings',
  });
  const updateMeeting = (id, field, value) => {
    onMeetingTimesChange(
      meetingTimes.map(m => (m.id === id ? { ...m, [field]: value } : m))
    );
  };
  const deleteMeeting = id =>
    onMeetingTimesChange(meetingTimes.filter(m => m.id !== id));

  const ids = meetingTimes.map(m => m.id);

  return (
    <section
      ref={setDroppableRef}
      className={`rounded-card border bg-surface-elevated overflow-hidden transition-colors ${isOver ? 'border-accent ring-1 ring-accent/30' : 'border-border'}`}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-muted">
        <h3 className="text-sm font-semibold text-ink-muted uppercase tracking-wider">
          Meeting times
        </h3>
        <button
          type="button"
          onClick={onOpenAddModal}
          className="rounded-button border border-border px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface hover:text-ink transition-colors"
        >
          + Add
        </button>
      </div>
      <div className="overflow-x-auto">
        {meetingTimes.length === 0 ? (
          <p className="px-4 py-6 text-sm text-ink-muted text-center">
            No meeting times. Add one if your syllabus includes a schedule.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-muted">
                <th className="w-8 px-2 py-2" aria-label="Reorder" />
                <th className="text-left font-medium text-ink px-3 py-2">
                  Day
                </th>
                <th className="text-left font-medium text-ink px-3 py-2">
                  Time
                </th>
                <th className="text-left font-medium text-ink px-3 py-2">
                  Location
                </th>
                <th className="text-left font-medium text-ink px-3 py-2">
                  Type
                </th>
                <th className="w-10 px-2 py-2" aria-label="Remove" />
              </tr>
            </thead>
            <tbody>
              <SortableContext
                items={ids}
                strategy={verticalListSortingStrategy}
              >
                {meetingTimes.map(m => (
                  <SortableMeetingRow
                    key={m.id}
                    meeting={m}
                    onUpdate={updateMeeting}
                    onDelete={deleteMeeting}
                  />
                ))}
              </SortableContext>
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

/** Section box: one assessment section (exams, assignments, etc.). */
function AssessmentSectionBox({
  sectionId,
  label,
  items,
  onUpdate,
  onDelete,
  onOpenAddModal,
}) {
  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: `section-${sectionId}`,
  });
  const ids = items.map(a => a.id);

  return (
    <section
      ref={setDroppableRef}
      className={`rounded-card border bg-surface-elevated overflow-hidden transition-colors ${isOver ? 'border-accent ring-1 ring-accent/30' : 'border-border'}`}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-muted">
        <h3 className="text-sm font-semibold text-ink-muted uppercase tracking-wider">
          {label}
        </h3>
        <button
          type="button"
          onClick={() => onOpenAddModal(sectionId)}
          className="rounded-button border border-border px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface hover:text-ink transition-colors"
        >
          + Add
        </button>
      </div>
      <div className="overflow-x-auto">
        {items.length === 0 ? (
          <p className="px-4 py-6 text-sm text-ink-muted text-center">
            None. Add one or drag from another section.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-muted">
                <th className="w-8 px-2 py-2" aria-label="Reorder" />
                <th className="text-left font-medium text-ink px-3 py-2">
                  Title
                </th>
                <th className="text-left font-medium text-ink px-3 py-2">
                  Type
                </th>
                <th className="text-left font-medium text-ink px-3 py-2">
                  Due date
                </th>
                <th
                  className="text-left font-medium text-ink px-3 py-2"
                  title="Estimated effort in hours (used by the scheduler; edit as needed)."
                >
                  Hours
                </th>
                <th className="w-10 px-2 py-2" aria-label="Remove" />
              </tr>
            </thead>
            <tbody data-section={sectionId}>
              <SortableContext
                items={ids}
                strategy={verticalListSortingStrategy}
              >
                {items.map(a => (
                  <SortableAssessmentRow
                    key={a.id}
                    item={a}
                    sectionId={sectionId}
                    onUpdate={onUpdate}
                    onDelete={onDelete}
                  />
                ))}
              </SortableContext>
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

export default function ParsedDataReview({
  courseName,
  instructors = [],
  onInstructorsChange,
  confidence = null,
  studyHoursPerWeek = '',
  onStudyHoursPerWeekChange,
  meetingTimes = [],
  onMeetingTimesChange,
  assignments,
  onAssignmentsChange,
  onConfirm,
  saving = false,
  saveError = '',
}) {
  const [addMeetingOpen, setAddMeetingOpen] = useState(false);
  const [addAssessmentOpen, setAddAssessmentOpen] = useState(false);
  const [addInstructorOpen, setAddInstructorOpen] = useState(false);
  const [addAssessmentSection, setAddAssessmentSection] =
    useState('assignments');
  const [activeId, setActiveId] = useState(null);

  const groups = groupBySection(assignments);

  const updateAssignment = (id, field, value) => {
    onAssignmentsChange(
      assignments.map(a => (a.id === id ? { ...a, [field]: value } : a))
    );
  };

  const deleteAssignment = id =>
    onAssignmentsChange(assignments.filter(a => a.id !== id));

  const addAssignment = (defaultType = 'assignment') => {
    const newId = `temp-${Date.now()}`;
    onAssignmentsChange([
      ...assignments,
      { id: newId, name: '', due: '', hours: 3, type: defaultType },
    ]);
  };

  const openAddAssessment = sectionId => {
    const typeBySection = {
      exams: 'midterm',
      projects: 'project',
      assignments: 'assignment',
      quizzes: 'quiz',
      participation: 'participation',
      other: 'assignment',
    };
    setAddAssessmentSection(sectionId);
    setAddAssessmentOpen(true);
  };

  const handleAddAssessmentFromModal = item => {
    onAssignmentsChange([...assignments, item]);
    setAddAssessmentOpen(false);
  };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const sectionToType = {
    exams: 'midterm',
    projects: 'project',
    assignments: 'assignment',
    quizzes: 'quiz',
    participation: 'participation',
    other: 'assignment',
  };

  const handleDragStart = ev => setActiveId(ev.active.id);

  const handleDragEnd = ev => {
    const { active, over } = ev;
    setActiveId(null);
    if (!over || active.id === over.id) return;

    const activeData = active.data?.current;
    const overId = String(over.id);

    if (activeData?.kind === 'meeting') {
      const fromIdx = meetingTimes.findIndex(m => m.id === active.id);
      const toIdx = meetingTimes.findIndex(m => m.id === overId);
      if (fromIdx === -1 || toIdx === -1) return;
      const next = [...meetingTimes];
      const [removed] = next.splice(fromIdx, 1);
      const insertIdx = toIdx > fromIdx ? toIdx - 1 : toIdx;
      next.splice(insertIdx, 0, removed);
      onMeetingTimesChange(next);
      return;
    }

    if (activeData?.kind === 'assessment') {
      const fromIdx = assignments.findIndex(a => a.id === active.id);
      if (fromIdx === -1) return;

      if (overId.startsWith('section-')) {
        const sectionId = overId.replace('section-', '');
        const newType = sectionToType[sectionId] || 'assignment';
        const updated = assignments.map((a, i) =>
          i === fromIdx ? { ...a, type: newType } : a
        );
        onAssignmentsChange(updated);
        return;
      }

      const toIdx = assignments.findIndex(a => a.id === overId);
      if (toIdx === -1) return;

      const activeSection =
        TYPE_TO_SECTION[assignments[fromIdx].type] || 'other';
      const overSection = TYPE_TO_SECTION[assignments[toIdx].type] || 'other';

      const next = [...assignments];
      const [removed] = next.splice(fromIdx, 1);
      const item =
        activeSection !== overSection
          ? { ...removed, type: sectionToType[overSection] || 'assignment' }
          : removed;
      const insertIdx = toIdx >= fromIdx ? toIdx - 1 : toIdx;
      next.splice(insertIdx, 0, item);
      onAssignmentsChange(next);
    }
  };

  const allMeetingIds = meetingTimes.map(m => m.id);
  const allAssignmentIds = assignments.map(a => a.id);

  const confidenceLabel = confidence?.label
    ? String(confidence.label).charAt(0).toUpperCase() +
      String(confidence.label).slice(1)
    : null;
  const confidenceScore =
    confidence?.score != null ? Number(confidence.score) : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-medium text-ink">{courseName}</h2>
        {confidenceLabel != null && (
          <span
            className="rounded-full px-2.5 py-0.5 text-xs font-medium bg-surface-muted text-ink-muted"
            title={
              confidenceScore != null
                ? `Parse confidence: ${confidenceScore}%`
                : 'Parse confidence'
            }
          >
            Confidence: {confidenceLabel}
            {confidenceScore != null ? ` (${confidenceScore}%)` : ''}
          </span>
        )}
      </div>
      {onStudyHoursPerWeekChange && (
        <section className="rounded-card border border-border bg-surface-elevated overflow-hidden">
          <div className="px-4 py-3 border-b border-border bg-surface-muted">
            <h3 className="text-sm font-semibold text-ink-muted uppercase tracking-wider">
              Course settings
            </h3>
          </div>
          <div className="px-4 py-3">
            <label className="block text-sm font-medium text-ink-muted mb-1">
              Study hours per week (optional)
            </label>
            <input
              type="number"
              min={0}
              max={168}
              placeholder="e.g. 10"
              value={studyHoursPerWeek}
              onChange={e => onStudyHoursPerWeekChange(e.target.value)}
              className="w-24 rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            <p className="text-xs text-ink-muted mt-1">
              Max hours the scheduler will allocate for this course per week.
              Leave blank for no cap.
            </p>
          </div>
        </section>
      )}
      {(instructors.length > 0 || onInstructorsChange) && (
        <section className="rounded-card border border-border bg-surface-elevated overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-muted">
            <h3 className="text-sm font-semibold text-ink-muted uppercase tracking-wider">
              Instructors & contact
            </h3>
            {onInstructorsChange && (
              <button
                type="button"
                onClick={() => setAddInstructorOpen(true)}
                className="rounded-button border border-border px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-surface hover:text-ink transition-colors"
              >
                + Add
              </button>
            )}
          </div>
          {instructors.length === 0 ? (
            <p className="px-4 py-4 text-sm text-ink-muted">
              No instructors extracted. Add one if your syllabus lists an
              instructor or TA.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {instructors.map((inst, i) => (
                <li
                  key={inst.id || i}
                  className="flex items-center justify-between gap-2 px-4 py-2 text-sm"
                >
                  <span>
                    <span className="font-medium text-ink">
                      {inst.name || 'Instructor'}
                    </span>
                    {inst.email && (
                      <span className="text-ink-muted ml-2">
                        <a
                          href={`mailto:${inst.email}`}
                          className="text-accent hover:underline"
                        >
                          {inst.email}
                        </a>
                      </span>
                    )}
                  </span>
                  {onInstructorsChange && (
                    <button
                      type="button"
                      onClick={() =>
                        onInstructorsChange(
                          instructors.filter((_, j) => j !== i)
                        )
                      }
                      className="rounded-button p-1.5 text-ink-muted hover:bg-red-500/10 hover:text-red-600"
                      title="Remove"
                      aria-label="Remove"
                    >
                      ×
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {saveError && (
        <div className="rounded-input bg-red-500/10 border border-red-500/30 px-3 py-2 text-sm text-red-600">
          {saveError}
        </div>
      )}
      <p className="text-sm text-ink-muted">
        Review and organize parsed data. Edit cells by clicking, add or remove
        rows, and drag items to reorder or move between sections.{' '}
        <span className="block mt-1">
          Hours are estimated effort per item for the scheduler—edit them to
          match how much time you plan to spend.
        </span>{' '}
        Then confirm to save.
      </p>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <MeetingTimesSection
          meetingTimes={meetingTimes}
          onMeetingTimesChange={onMeetingTimesChange}
          onOpenAddModal={() => setAddMeetingOpen(true)}
        />

        {SECTION_ORDER.map(section => (
          <AssessmentSectionBox
            key={section}
            sectionId={section}
            label={SECTION_LABELS[section]}
            items={groups[section]}
            onUpdate={updateAssignment}
            onDelete={deleteAssignment}
            onOpenAddModal={openAddAssessment}
          />
        ))}

        <DragOverlay>
          {activeId ? (
            allMeetingIds.includes(activeId) ? (
              <table className="w-full text-sm border border-border rounded bg-surface-elevated shadow-lg">
                <tbody>
                  {(() => {
                    const m = meetingTimes.find(x => x.id === activeId);
                    if (!m) return null;
                    const dayLabel =
                      DAYS.find(d => d.value === m.day_of_week)?.label ||
                      m.day_of_week;
                    const timeDisplay =
                      m.start_time && m.end_time
                        ? `${m.start_time} – ${m.end_time}`
                        : 'TBD';
                    return (
                      <tr className="border-b border-border-subtle bg-surface-elevated">
                        <td className="w-8 px-2 py-2 text-ink-muted">⋮⋮</td>
                        <td className="px-3 py-2">{dayLabel}</td>
                        <td className="px-3 py-2">{timeDisplay}</td>
                        <td className="px-3 py-2">{m.location || '—'}</td>
                        <td className="px-3 py-2">
                          {MEETING_TYPES.find(
                            t => t.value === (m.type || 'lecture')
                          )?.label || m.type}
                        </td>
                        <td className="w-10" />
                      </tr>
                    );
                  })()}
                </tbody>
              </table>
            ) : (
              <table className="w-full text-sm border border-border rounded bg-surface-elevated shadow-lg">
                <tbody>
                  {(() => {
                    const a = assignments.find(x => x.id === activeId);
                    if (!a) return null;
                    return (
                      <tr className="border-b border-border-subtle bg-surface-elevated">
                        <td className="w-8 px-2 py-2 text-ink-muted">⋮⋮</td>
                        <td className="px-3 py-2">{a.name}</td>
                        <td className="px-3 py-2">{a.type || 'assignment'}</td>
                        <td className="px-3 py-2">
                          {a.due || a.due_date || '—'}
                        </td>
                        <td className="px-3 py-2">{a.hours}</td>
                        <td className="w-10" />
                      </tr>
                    );
                  })()}
                </tbody>
              </table>
            )
          ) : null}
        </DragOverlay>
      </DndContext>

      <AddMeetingModal
        open={addMeetingOpen}
        onClose={() => setAddMeetingOpen(false)}
        onAdd={item => onMeetingTimesChange([...meetingTimes, item])}
      />
      <AddInstructorModal
        open={addInstructorOpen}
        onClose={() => setAddInstructorOpen(false)}
        onAdd={inst =>
          onInstructorsChange && onInstructorsChange([...instructors, inst])
        }
      />
      <AddAssessmentModal
        open={addAssessmentOpen}
        onClose={() => setAddAssessmentOpen(false)}
        onAdd={handleAddAssessmentFromModal}
        defaultType={
          addAssessmentSection === 'exams'
            ? 'midterm'
            : addAssessmentSection === 'projects'
              ? 'project'
              : addAssessmentSection === 'quizzes'
                ? 'quiz'
                : addAssessmentSection === 'participation'
                  ? 'participation'
                  : 'assignment'
        }
      />

      <div className="flex justify-end pt-2">
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
