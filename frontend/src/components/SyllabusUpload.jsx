/**
 * Upload PDF/DOCX/TXT or paste syllabus text. Calls parse API and onComplete with parsed data.
 */
import { useState } from 'react';
import { parseSyllabus } from '../api/client';

/** Renders upload/paste form. onComplete({ course_name, meeting_times, assignments }) when parse succeeds. */
const ACCEPT = '.pdf,.docx,.txt';

export default function SyllabusUpload({ onComplete, token }) {
  const [mode, setMode] = useState('file');
  const [file, setFile] = useState(null);
  const [paste, setPaste] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const acceptFile = f => {
    if (!f) return false;
    const ext = (f.name || '').toLowerCase().slice(-4);
    return ext === '.pdf' || ext === '.txt' || ext.endsWith('.docx');
  };

  const handleDrop = e => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer?.files?.[0];
    if (f && acceptFile(f)) setFile(f);
  };

  const handleDragOver = e => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  /** Infer default hours from assessment type. */
  const hoursFromType = (type) => {
    const t = (type || '').toLowerCase();
    if (t === 'midterm' || t === 'final') return 2;
    if (t === 'quiz') return 1;
    if (t === 'project') return 4;
    return 3;
  };

  /** Handles form submit. Calls real parse API. Uses assessments when present for types/exams. */
  const handleSubmit = async e => {
    e.preventDefault();
    setError(null);
    setUploading(true);
    try {
      const payload = mode === 'file' ? { file } : { text: paste.trim() };
      const data = await parseSyllabus(token, payload);
      const courseName = data.course_name || 'Course';
      // Prefer assessments from full parser (includes type, due_datetime, exams)
      const raw =
        Array.isArray(data.assessments) && data.assessments.length > 0
          ? data.assessments.map((a) => ({
              name: a.title || '',
              due_date: a.due_datetime ? String(a.due_datetime).slice(0, 10) : '',
              hours: hoursFromType(a.type),
              type: a.type || 'assignment',
              confidence: typeof a.confidence === 'number' ? a.confidence : null,
            }))
          : (data.assignments || []).map((a) => ({
              name: a.name || '',
              due_date: a.due_date || '',
              hours: a.hours ?? 3,
              type: a.type || 'assignment',
              confidence: typeof a.confidence === 'number' ? a.confidence : null,
            }));
      const assignments = raw.map((a, i) => ({
        id: `temp-${i}`,
        name: a.name || '',
        due: a.due_date || '',
        hours: a.hours ?? 3,
        type: a.type || 'assignment',
        confidence: a.confidence ?? null,
      }));
      const meeting_times = Array.isArray(data.meeting_times) ? data.meeting_times : [];
      const instructors = Array.isArray(data.instructors) ? data.instructors : [];
      const confidence = data.confidence || null;
      onComplete({ course_name: courseName, meeting_times, assignments, instructors, confidence });
    } catch (err) {
      setError(err.message || 'Parse failed');
    } finally {
      setUploading(false);
    }
  };

  const canSubmit = mode === 'file' ? file : paste.trim().length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-input bg-red-500/10 border border-red-500/30 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}
      <div className="flex gap-2 border-b border-border pb-2">
        <button
          type="button"
          onClick={() => setMode('file')}
          className={`rounded-button px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
            mode === 'file'
              ? 'bg-accent-muted text-accent'
              : 'text-ink-muted hover:text-ink'
          }`}
        >
          Upload file
        </button>
        <button
          type="button"
          onClick={() => setMode('paste')}
          className={`rounded-button px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
            mode === 'paste'
              ? 'bg-accent-muted text-accent'
              : 'text-ink-muted hover:text-ink'
          }`}
        >
          Paste text
        </button>
      </div>

      {mode === 'file' && (
        <div className="animate-fade-in">
          <label
            className={`block rounded-input border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-200 ${
              dragOver ? 'border-accent bg-accent-muted/30' : 'border-border bg-surface-muted hover:border-accent/40'
            }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <input
              type="file"
              accept={ACCEPT}
              className="hidden"
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
            <span className="text-sm text-ink-muted">
              {file ? file.name : 'Drop PDF, DOCX, or TXT here — or click to browse'}
            </span>
          </label>
        </div>
      )}

      {mode === 'paste' && (
        <div className="animate-fade-in">
          <textarea
            value={paste}
            onChange={e => setPaste(e.target.value)}
            placeholder="Paste syllabus text here…"
            rows={8}
            className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent           resize-y"
          />
        </div>
      )}

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={!canSubmit || uploading}
          className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {uploading ? 'Parsing…' : 'Parse syllabus'}
        </button>
      </div>
    </form>
  );
}
