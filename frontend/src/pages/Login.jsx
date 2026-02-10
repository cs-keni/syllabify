/**
 * Login page. Validates credentials via AuthContext, redirects to Dashboard or SecuritySetup.
 * DISCLAIMER: Project structure may change. Functions may be added or modified.
 */
import { useState } from 'react';
import { useNavigate, Link, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

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
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface px-4">
      <div className="mx-auto max-w-sm w-full space-y-8">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-ink">Log in</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Use your account to access your schedules.
          </p>
        </div>
        <form
          onSubmit={handleSubmit}
          className="rounded-card bg-surface-elevated border border-border p-6 shadow-card space-y-4"
        >
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-button px-3 py-2">
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
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-button bg-accent py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
          >
            {submitting ? 'Logging in…' : 'Log in'}
          </button>
          <p className="text-center text-sm text-ink-muted">
            New? You can create an account later. For now use the dev client to
            log in.
          </p>
        </form>
        <p className="text-center">
          <Link
            to="/"
            className="text-sm text-ink-muted no-underline hover:text-ink"
          >
            Syllabify
          </Link>
        </p>
      </div>
    </div>
  );
}
