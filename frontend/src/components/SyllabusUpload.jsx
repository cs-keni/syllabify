/**
 * Upload PDF or paste syllabus text. Simulates parse (real API TODO). Calls onComplete with course name.
 * DISCLAIMER: Project structure may change. Functions may be added or modified.
 */
import { useState } from 'react';

/** Renders upload/paste form. onComplete(courseName) called when parse succeeds. */
export default function SyllabusUpload({ onComplete }) {
  const [mode, setMode] = useState('file');
  const [file, setFile] = useState(null);
  const [paste, setPaste] = useState('');
  const [uploading, setUploading] = useState(false);

  /** Handles form submit. Simulates API parse, then calls onComplete. */
  const handleSubmit = e => {
    e.preventDefault();
    setUploading(true);
    // Simulate parse; in real app call API
    setTimeout(() => {
      setUploading(false);
      onComplete('CS 422');
    }, 800);
  };

  const canSubmit = mode === 'file' ? file : paste.trim().length > 0;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
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
          Upload PDF
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
          <label className="block rounded-input border-2 border-dashed border-border bg-surface-muted p-8 text-center cursor-pointer hover:border-accent/40 hover:scale-[1.01] transition-all duration-200">
            <input
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
            <span className="text-sm text-ink-muted">
              {file ? file.name : 'Drop a PDF or click to browse'}
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
