/**
 * Upload page: multi-step flow (upload → review → confirm). Uses SyllabusUpload and ParsedDataReview.
 * DISCLAIMER: Project structure may change. Components/steps may be added or modified.
 */
import { useState } from 'react';
import SyllabusUpload from '../components/SyllabusUpload';
import ParsedDataReview from '../components/ParsedDataReview';

const STEPS = [
  { id: 'upload', label: 'Upload' },
  { id: 'review', label: 'Review' },
  { id: 'confirm', label: 'Confirm' },
];

const MOCK_ASSIGNMENTS = [
  { id: '1', name: 'Assignment 1', due: '2025-02-01', hours: 4 },
  { id: '2', name: 'Assignment 2', due: '2025-02-08', hours: 5 },
  { id: '3', name: 'Midterm', due: '2025-02-15', hours: 2 },
];

/** Step-based upload flow. Manages step state, parsed course name, and assignments. */
export default function Upload() {
  const [step, setStep] = useState(0);
  const [assignments, setAssignments] = useState(MOCK_ASSIGNMENTS);
  const [parsedCourseName, setParsedCourseName] = useState('');

  const currentStepId = STEPS[step].id;

  return (
    <div className="space-y-8">
      <div className="animate-fade-in">
        <h1 className="text-2xl font-semibold text-ink">Upload syllabus</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Upload a PDF or paste text, then review and confirm the extracted
          data.
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
              onComplete={courseName => {
                setParsedCourseName(courseName);
                setStep(1);
              }}
            />
          )}
          {currentStepId === 'review' && (
            <ParsedDataReview
              courseName={parsedCourseName || 'Course'}
              assignments={assignments}
              onAssignmentsChange={setAssignments}
              onConfirm={() => setStep(2)}
            />
          )}
          {currentStepId === 'confirm' && (
            <div className="space-y-4">
              <h2 className="text-lg font-medium text-ink">All set</h2>
              <p className="text-sm text-ink-muted">
                You’ve confirmed {assignments.length} assignment
                {assignments.length !== 1 ? 's' : ''}. You can generate a
                schedule from the Schedule page or add another syllabus.
              </p>
              <button
                type="button"
                onClick={() => setStep(0)}
                className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors duration-200"
              >
                Upload another
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
