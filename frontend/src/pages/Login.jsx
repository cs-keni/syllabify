/**
 * Login page. Validates credentials via AuthContext, redirects to Dashboard or SecuritySetup.
 * DISCLAIMER: Project structure may change. Functions may be added or modified.
 */
import { useState } from 'react';
import { useNavigate, Link, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import logo from '../assets/syllabify-logo-green.png';
import ThemeToggle from '../components/ThemeToggle';

/** Login form. Uses AuthContext.login, redirects based on security_setup_done. */
export default function Login() {
  const { user, securitySetupDone, login } = useAuth();
  const navigate = useNavigate();
  if (user && securitySetupDone) return <Navigate to="/app" replace />;
  if (user && !securitySetupDone)
    return <Navigate to="/security-setup" replace />;
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  /** Submits credentials, calls login, navigates on success. */
  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const result = await login(username.trim(), password);
      if (result.security_setup_done) {
        navigate('/app', { replace: true });
      } else {
        navigate('/security-setup', { replace: true });
      }
    } catch (err) {
      setError(err.message || 'Invalid credentials');
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface text-ink">
      <header className="border-b border-border bg-surface-elevated shadow-card">
        <div className="relative mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-1.5 sm:py-4">
          <div className="sm:hidden space-y-1.5">
            <div className="relative flex items-center justify-between gap-1.5">
              <Link
                to="/"
                className="text-base font-semibold tracking-tight text-ink no-underline hover:text-accent"
              >
                Syllabify
              </Link>
              <ThemeToggle />
              <div className="pointer-events-none absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2">
                <img
                  src={logo}
                  alt="Syllabify"
                  className="h-40 w-40 object-contain animate-scale-in"
                />
              </div>
            </div>
            <Link
              to="/"
              className="block text-center rounded-button border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink no-underline hover:bg-surface-muted"
            >
              Back to home
            </Link>
          </div>
          <div className="relative hidden sm:flex items-center justify-between gap-3">
            <Link
              to="/"
              className="text-lg font-semibold tracking-tight text-ink no-underline hover:text-accent"
            >
              Syllabify
            </Link>
            <div className="pointer-events-none absolute left-1/2 -translate-x-1/2">
              <img
                src={logo}
                alt="Syllabify"
                className="h-28 w-28 md:h-40 md:w-40 lg:h-48 lg:w-48 object-contain animate-scale-in"
              />
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <Link
                to="/"
                className="rounded-button border border-border bg-surface px-4 py-2.5 text-sm font-medium text-ink no-underline hover:bg-surface-muted"
              >
                Back to home
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 pb-12 sm:pb-16 pt-8 sm:pt-10">
        <div className="mx-auto max-w-md">
          <div className="text-center animate-fade-in">
            <p className="text-sm uppercase tracking-[0.2em] text-accent">
              Welcome back
            </p>
            <h1 className="mt-3 text-3xl sm:text-4xl font-serif font-semibold text-ink">
              Log in to Syllabify
            </h1>
            <p className="mt-3 text-sm sm:text-base text-ink-muted">
              Use your account to access your schedules.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="mt-6 sm:mt-8 rounded-3xl border border-border bg-surface-elevated p-5 sm:p-8 shadow-card space-y-4 animate-fade-in-up [animation-delay:200ms]"
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
                className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder="syllabify-client"
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
                autoComplete="current-password"
                className="w-full rounded-input border border-border bg-surface px-3 py-2 text-ink text-sm placeholder:text-ink-subtle focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
                placeholder="password"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-button bg-accent py-2.5 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-60 transition-colors duration-200"
            >
              {submitting ? 'Logging in...' : 'Log in'}
            </button>
            <p className="text-center text-sm text-ink-muted">
              New? You can create an account later. For now use the dev client
              to log in.
            </p>
          </form>
        </div>
      </main>
    </div>
  );
}
