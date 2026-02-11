/**
 * Login page. Validates credentials via AuthContext, redirects to Dashboard or SecuritySetup.
 * DISCLAIMER: Project structure may change. Functions may be added or modified.
 */
import { useState } from 'react';
import { useNavigate, Link, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import logo from '../assets/syllabify-logo.jpg';

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
    <div className="min-h-screen bg-black text-white">
      <header className="bg-gradient-to-r from-blue-900 via-blue-800 to-blue-700 shadow-lg">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-6">
          <div className="relative flex items-center justify-between">
            <Link
              to="/"
              className="text-lg font-semibold tracking-tight text-white no-underline"
            >
              Syllabify
            </Link>
            <div className="absolute left-1/2 translate-y-1.5 -translate-x-1/2">
              <img
                src={logo}
                alt="Syllabify"
                className="h-[256px] w-[256px] object-contain"
              />
            </div>
            <Link
              to="/"
              className="rounded-button bg-white px-4 py-2 text-sm font-medium text-blue-900 no-underline hover:bg-blue-50"
            >
              Back to home
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 pb-16 pt-10">
        <div className="mx-auto max-w-md">
          <div className="text-center">
            <p className="text-sm uppercase tracking-[0.2em] text-blue-300">
              Welcome back
            </p>
            <h1 className="mt-3 text-3xl sm:text-4xl font-serif font-semibold text-white">
              Log in to Syllabify
            </h1>
            <p className="mt-3 text-sm sm:text-base text-blue-200">
              Use your account to access your schedules.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="mt-8 rounded-3xl border border-blue-900/40 bg-blue-950/40 p-6 sm:p-8 shadow-xl shadow-blue-900/30 space-y-4"
          >
            {error && (
              <p className="text-sm text-red-200 bg-red-900/40 border border-red-800/60 rounded-button px-3 py-2">
                {error}
              </p>
            )}
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-blue-200 mb-1"
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
                className="w-full rounded-input border border-blue-900/50 bg-blue-950/70 px-3 py-2 text-white text-sm placeholder:text-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-blue-300"
                placeholder="syllabify-client"
              />
            </div>
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-blue-200 mb-1"
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
                className="w-full rounded-input border border-blue-900/50 bg-blue-950/70 px-3 py-2 text-white text-sm placeholder:text-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-blue-300"
                placeholder="password"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-button bg-white py-2 text-sm font-medium text-blue-900 hover:bg-blue-50 disabled:opacity-60"
            >
              {submitting ? 'Logging in...' : 'Log in'}
            </button>
            <p className="text-center text-sm text-blue-200">
              New? You can create an account later. For now use the dev client
              to log in.
            </p>
          </form>
        </div>
      </main>
    </div>
  );
}
