/**
 * Upload page: multi-step flow (upload → review → confirm). Uses SyllabusUpload and ParsedDataReview.
 * Reads courseId/courseName from location.state when navigated from a Course page.
 * DISCLAIMER: Project structure may change. Components/steps may be added or modified.
 */
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import SyllabusUpload from '../components/SyllabusUpload';
import ParsedDataReview from '../components/ParsedDataReview';
import { addAssignments, saveCourse } from '../api/client';

const STEPS = [
  { id: 'upload', label: 'Upload' },
  { id: 'review', label: 'Review' },
  { id: 'confirm', label: 'Confirm' },
];

/** Step-based upload flow. Manages step state, parsed course name, and assignments. */
export default function Upload() {
  const { token } = useAuth();
  const { state } = useLocation();
  const navigate = useNavigate();
  const [createdCourseId, setCreatedCourseId] = useState(null);
  const courseId = state?.courseId ?? createdCourseId;
  const initialCourseName = state?.courseName ?? '';
  const [step, setStep] = useState(0);
  const [assignments, setAssignments] = useState([]);
  const [parsedCourseName, setParsedCourseName] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const currentStepId = STEPS[step].id;

  /** Called by SyllabusUpload with { course_name, assignments } from real API. */
  const handleUploadComplete = ({ course_name, assignments: parsed }) => {
    setParsedCourseName(course_name || initialCourseName);
    setAssignments(parsed || []);
    setStep(1);
  };

  /** Saves assignments to DB if courseId present, then advances to confirm step. */
  const handleConfirm = async () => {
    if (!courseId) {
      setStep(2);
      return;
    }
    setSaving(true);
    setSaveError('');
    try {
      await addAssignments(courseId, assignments);
      setStep(2);
    } catch (e) {
      setSaveError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="animate-fade-in">
        <h1 className="text-2xl font-semibold text-ink">Upload syllabus</h1>
        <p className="mt-1 text-sm text-ink-muted">
          {initialCourseName
            ? `Uploading syllabus for ${initialCourseName}.`
            : 'Upload a PDF or paste text, then review and confirm the extracted data.'}
        </p>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s.id} className="flex items-center">
            <button
              type="button"
              onClick={() => setStep(i)}
              className={`rounded-button px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
                i === step
                  ? 'bg-accent text-white'
                  : i < step
                    ? 'bg-accent-muted text-accent'
                    : 'bg-surface-muted text-ink-muted hover:text-ink'
              }`}
            >
              {s.label}
            </button>
            {i < STEPS.length - 1 && (
              <span
                className={`mx-1 w-6 h-0.5 rounded ${
                  i < step ? 'bg-accent' : 'bg-border'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="rounded-card bg-surface-elevated border border-border p-6 shadow-card min-h-[320px]">
        <div key={currentStepId} className="animate-fade-in">
          {currentStepId === 'upload' && (
            <SyllabusUpload
              token={token}
              onComplete={(courseName, parsedAssignments) => {
                setParsedCourseName(courseName);
                setAssignments(parsedAssignments || []);
                setStep(1);
              }}
            />
          )}
          {currentStepId === 'review' && (
            <ParsedDataReview
              courseName={parsedCourseName || 'Course'}
              assignments={assignments}
              onAssignmentsChange={setAssignments}
              onConfirm={async () => {
                setSaveError(null);
                setSaving(true);
                try {
                  const result = await saveCourse(token, {
                    course_name: parsedCourseName || 'Course',
                    assignments,
                  });
                  if (result?.id) setCreatedCourseId(result.id);
                  setStep(2);
                } catch (err) {
                  setSaveError(err.message || 'Failed to save');
                } finally {
                  setSaving(false);
                }
              }}
              saving={saving}
              saveError={saveError}
            />
          )}
          {currentStepId === 'confirm' && (
            <div className="space-y-4">
              <h2 className="text-lg font-medium text-ink">All set</h2>
              <p className="text-sm text-ink-muted">
                You've confirmed {assignments.length} assignment
                {assignments.length !== 1 ? 's' : ''}.
              </p>
              <div className="flex gap-3">
                {courseId && (
                  <button
                    type="button"
                    onClick={() => navigate(`/app/courses/${courseId}`)}
                    className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors duration-200"
                  >
                    View course
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setStep(0);
                    setAssignments([]);
                    setParsedCourseName(initialCourseName);
                  }}
                  className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:text-ink transition-colors duration-200"
                >
                  Upload another
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
