import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../api/client';
import ThemeToggle from '../components/ThemeToggle';
import Footer from '../components/Footer';

const REQUIREMENTS = [
  { key: 'length', test: p => p.length >= 8, label: 'At least 8 characters' },
  { key: 'upper', test: p => /[A-Z]/.test(p), label: 'One uppercase letter' },
  { key: 'lower', test: p => /[a-z]/.test(p), label: 'One lowercase letter' },
  { key: 'number', test: p => /\d/.test(p), label: 'One number' },
  {
    key: 'special',
    test: p => /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(p),
    label: 'One special character',
  },
];

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const reqStatus = REQUIREMENTS.map(r => ({ ...r, met: r.test(password) }));
  const allMet = reqStatus.every(r => r.met);

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    if (!allMet) {
      setError('Password does not meet all requirements');
      return;
    }
    if (!token) {
      setError(
        'Missing reset token. Please start the forgot-password flow again.'
      );
      return;
    }
    setSubmitting(true);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err.message || 'Reset failed. Your link may have expired.');
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
              Set new password
            </h1>
            <p className="mt-2 text-sm text-ink-muted">
              Choose a strong password for your account.
            </p>
          </div>

          <div className="mt-8 rounded-3xl border border-border bg-surface-elevated p-6 shadow-card space-y-4 animate-fade-in-up [animation-delay:200ms]">
            {done ? (
              <div className="text-center space-y-4 py-2">
                <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                  Password updated successfully!
                </p>
                <Link
                  to="/login"
                  className="inline-block rounded-button bg-[#0F8A4C] px-6 py-2.5 text-sm font-medium text-white hover:bg-[#094728] transition-colors no-underline"
                >
                  Log in
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <p className="text-sm text-red-700 bg-red-50 dark:text-red-300 dark:bg-red-900/30 border border-red-200 dark:border-red-800/60 rounded-button px-3 py-2">
                    {error}
                  </p>
                )}
                <div>
                  <label
                    htmlFor="password"
                    className="block text-sm font-medium text-ink mb-1"
                  >
                    New password
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                  />
                  {password && (
                    <ul className="mt-2 space-y-1">
                      {reqStatus.map(r => (
                        <li
                          key={r.key}
                          className={`text-xs flex items-center gap-1.5 ${r.met ? 'text-green-600 dark:text-green-400' : 'text-ink-muted'}`}
                        >
                          <span>{r.met ? '✓' : '○'}</span> {r.label}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <label
                    htmlFor="confirm"
                    className="block text-sm font-medium text-ink mb-1"
                  >
                    Confirm password
                  </label>
                  <input
                    id="confirm"
                    type="password"
                    value={confirm}
                    onChange={e => setConfirm(e.target.value)}
                    required
                    autoComplete="new-password"
                    className="w-full rounded-input border border-border bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                  />
                </div>
                <button
                  type="submit"
                  disabled={submitting || !allMet}
                  className="w-full rounded-button bg-[#0F8A4C] py-2.5 text-sm font-medium text-white hover:bg-[#094728] disabled:opacity-60 transition-colors"
                >
                  {submitting ? 'Saving…' : 'Set new password'}
                </button>
              </form>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
