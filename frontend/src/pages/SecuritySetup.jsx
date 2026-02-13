/**
 * One-time security questions setup. Requires auth. Calls completeSecuritySetup from AuthContext.
 * DISCLAIMER: Project structure may change. Functions may be added or modified.
 */
import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const DEFAULT_QUESTIONS = [
  { question: '', answer: '' },
  { question: '', answer: '' },
];

/** Security setup form. Up to 5 Q&A pairs. Submits via AuthContext.completeSecuritySetup. */
export default function SecuritySetup() {
  const { user, securitySetupDone, completeSecuritySetup } = useAuth();
  const navigate = useNavigate();
  const [questions, setQuestions] = useState(DEFAULT_QUESTIONS);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  if (!user) return <Navigate to="/login" replace />;
  if (securitySetupDone) return <Navigate to="/app" replace />;

  /** Updates a single question or answer at index i. */
  const update = (i, field, value) => {
    const next = [...questions];
    next[i] = { ...next[i], [field]: value };
    setQuestions(next);
  };

  /** Adds a new empty Q&A pair (max 5). */
  const addQuestion = () => {
    if (questions.length < 5)
      setQuestions([...questions, { question: '', answer: '' }]);
  };

  /** Removes Q&A pair at index i. Keeps at least one. */
  const removeQuestion = i => {
    if (questions.length > 1) setQuestions(questions.filter((_, j) => j !== i));
  };

  /** Validates, calls completeSecuritySetup, redirects to Dashboard on success. */
  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    const filled = questions.filter(
      q => (q.question || '').trim() && (q.answer || '').trim()
    );
    if (filled.length < 1) {
      setError('At least one question and answer is required.');
      return;
    }
    setSubmitting(true);
    try {
      await completeSecuritySetup(filled);
      navigate('/app', { replace: true });
    } catch (err) {
      setError(err.message || 'Something went wrong.');
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-8">
      <div className="text-center animate-fade-in">
        <h1 className="text-2xl font-semibold text-ink">Security setup</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Set up security questions (one-time). Answers are stored securely.
        </p>
      </div>
      <form
        onSubmit={handleSubmit}
        className="rounded-card bg-surface-elevated border border-border p-6 shadow-card space-y-4 animate-fade-in-up [animation-delay:100ms]"
      >
        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-button px-3 py-2">
            {error}
          </p>
        )}
        {questions.map((qa, i) => (
          <div key={i} className="space-y-2">
            <label className="block text-sm font-medium text-ink">
              Question {i + 1}
            </label>
            <input
              type="text"
              value={qa.question}
              onChange={e => update(i, 'question', e.target.value)}
              placeholder="e.g. What city were you born in?"
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent mb-2"
            />
            <input
              type="text"
              value={qa.answer}
              onChange={e => update(i, 'answer', e.target.value)}
              placeholder="Your answer"
              className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            />
            {questions.length > 1 && (
              <button
                type="button"
                onClick={() => removeQuestion(i)}
                className="text-sm text-ink-muted hover:text-ink"
              >
                Remove
              </button>
            )}
          </div>
        ))}
        {questions.length < 5 && (
          <button
            type="button"
            onClick={addQuestion}
            className="text-sm font-medium text-accent hover:text-accent-hover"
          >
            Add another question
          </button>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-button bg-accent py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50 transition-colors duration-200"
        >
          {submitting ? 'Saving…' : 'Save and continue'}
        </button>
      </form>
    </div>
  );
}
