import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getSecurityQuestions, verifySecurityAnswer } from '../api/client';
import ThemeToggle from '../components/ThemeToggle';
import Footer from '../components/Footer';

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [step, setStep] = useState('username'); // 'username' | 'answer'
  const [username, setUsername] = useState('');
  const [questions, setQuestions] = useState([]);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleFetchQuestions = async e => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const data = await getSecurityQuestions(username.trim());
      if (!data.questions?.length) {
        setError('No security questions found for this username.');
        return;
      }
      setQuestions(data.questions);
      setSelectedQuestion(data.questions[0]);
      setStep('answer');
    } catch (err) {
      setError(err.message || 'Failed to load security questions');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async e => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const data = await verifySecurityAnswer(
        username.trim(),
        selectedQuestion.id,
        answer.trim()
      );
      navigate(`/reset-password?token=${encodeURIComponent(data.reset_token)}`);
    } catch (err) {
      setError('Incorrect answer. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface text-ink">
      <header className="border-b border-border bg-surface-elevated shadow-card">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
          <Link
            to="/"
            className="text-base font-semibold tracking-tight text-ink no-underline hover:text-accent"
          >
            Syllabify
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 pb-16 pt-10 w-full">
        <div className="mx-auto max-w-md">
          <div className="text-center animate-fade-in">
            <h1 className="text-3xl font-serif font-semibold text-ink">
              Forgot password?
            </h1>
            <p className="mt-2 text-sm text-ink-muted">
              {step === 'username'
                ? 'Enter your username to retrieve your security question.'
                : 'Answer your security question to get a reset link.'}
            </p>
          </div>

          <div className="mt-8 rounded-3xl border border-border bg-surface-elevated p-6 shadow-card space-y-4 animate-fade-in-up [animation-delay:200ms]">
            {error && (
              <p className="text-sm text-red-700 bg-red-50 dark:text-red-300 dark:bg-red-900/30 border border-red-200 dark:border-red-800/60 rounded-button px-3 py-2">
                {error}
              </p>
            )}

            {step === 'username' ? (
              <form onSubmit={handleFetchQuestions} className="space-y-4">
                <div>
                  <label
                    htmlFor="username"
                    className="block text-sm font-medium text-ink mb-1"
                  >
                    Username
                  </label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    required
                    autoComplete="username"
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                    placeholder="Your username"
                  />
                </div>
                <button
                  type="submit"
                  disabled={submitting || !username.trim()}
                  className="w-full rounded-button bg-[#0F8A4C] py-2.5 text-sm font-medium text-white hover:bg-[#094728] disabled:opacity-60 transition-colors"
                >
                  {submitting ? 'Looking up…' : 'Continue'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleVerify} className="space-y-4">
                {questions.length > 1 && (
                  <div>
                    <label className="block text-sm font-medium text-ink mb-1">
                      Security question
                    </label>
                    <select
                      value={selectedQuestion?.id}
                      onChange={e =>
                        setSelectedQuestion(
                          questions.find(q => q.id === Number(e.target.value))
                        )
                      }
                      className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                    >
                      {questions.map(q => (
                        <option key={q.id} value={q.id}>
                          {q.text}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {questions.length === 1 && (
                  <p className="text-sm font-medium text-ink bg-surface-muted rounded-button px-3 py-2">
                    {questions[0].text}
                  </p>
                )}
                <div>
                  <label
                    htmlFor="answer"
                    className="block text-sm font-medium text-ink mb-1"
                  >
                    Your answer
                  </label>
                  <input
                    id="answer"
                    type="text"
                    value={answer}
                    onChange={e => setAnswer(e.target.value)}
                    required
                    autoComplete="off"
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                    placeholder="Your answer"
                  />
                </div>
                <button
                  type="submit"
                  disabled={submitting || !answer.trim()}
                  className="w-full rounded-button bg-[#0F8A4C] py-2.5 text-sm font-medium text-white hover:bg-[#094728] disabled:opacity-60 transition-colors"
                >
                  {submitting ? 'Verifying…' : 'Verify answer'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStep('username');
                    setError('');
                    setAnswer('');
                  }}
                  className="w-full text-sm text-ink-muted hover:text-ink transition-colors"
                >
                  ← Back
                </button>
              </form>
            )}

            <p className="text-center text-sm text-ink-muted pt-2">
              Remember your password?{' '}
              <Link
                to="/login"
                className="text-accent hover:underline font-medium"
              >
                Log in
              </Link>
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
