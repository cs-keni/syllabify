/**
 * Registration page. Creates account, redirects to login.
 */
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import logo from '../assets/syllabify-logo-green.png';
import ThemeToggle from '../components/ThemeToggle';
import { register } from '../api/client';

export default function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    setSubmitting(true);
    try {
      await register(username.trim(), password);
      navigate('/login', {
        replace: true,
        state: { message: 'Account created. Log in.' },
      });
    } catch (err) {
      setError(err.message || 'Registration failed');
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface text-ink">
      <header className="border-b border-border bg-surface-elevated shadow-card">
        <div className="relative mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-1.5 sm:py-4">
          <div className="flex items-center justify-between gap-3">
            <Link
              to="/"
              className="text-lg font-semibold tracking-tight text-ink no-underline hover:text-accent"
            >
              Syllabify
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 pb-12 pt-8">
        <div className="mx-auto max-w-md">
          <div className="text-center animate-fade-in">
            <p className="text-sm uppercase tracking-[0.2em] text-accent">
              Create account
            </p>
            <h1 className="mt-3 text-3xl font-serif font-semibold text-ink">
              Sign up for Syllabify
            </h1>
            <p className="mt-3 text-sm text-ink-muted">
              Create an account to manage your syllabi and schedules.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="mt-6 rounded-3xl border border-border bg-surface-elevated p-5 sm:p-8 shadow-card space-y-4 animate-fade-in-up [animation-delay:200ms]"
          >
            {error && (
              <p className="text-sm text-red-700 bg-red-50 dark:text-red-300 dark:bg-red-900/30 border border-red-200 dark:border-red-800/60 rounded-button px-3 py-2 animate-slide-down">
                {error}
              </p>
            )}
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
                minLength={3}
                maxLength={50}
                className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder="3-50 chars, letters, numbers, underscore"
              />
            </div>
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-ink mb-1"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                minLength={8}
                className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder="At least 8 characters"
              />
            </div>
            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-ink mb-1"
              >
                Confirm password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder="Re-enter password"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-button bg-[#0F8A4C] py-2.5 text-sm font-medium text-white hover:bg-[#094728] disabled:opacity-60 transition-colors duration-200"
            >
              {submitting ? 'Creating account...' : 'Sign up'}
            </button>
            <p className="text-center text-sm text-ink-muted">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-accent hover:underline font-medium"
              >
                Log in
              </Link>
            </p>
          </form>
        </div>
      </main>
    </div>
  );
}
