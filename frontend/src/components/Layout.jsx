/**
 * App shell: nav bar + main content. Requires auth; redirects to Login or SecuritySetup.
 * DISCLAIMER: Project structure may change. Components may be added or modified.
 */
import { Outlet, NavLink, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ThemeToggle from './ThemeToggle';

const navItems = [
  { to: '/app', label: 'Dashboard' },
  { to: '/app/upload', label: 'Upload syllabus' },
  { to: '/app/schedule', label: 'Schedule' },
  { to: '/app/preferences', label: 'Preferences' },
];

/** Main layout with header nav and Outlet for child routes. */
export default function Layout() {
  const { user, securitySetupDone, logout } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!securitySetupDone) return <Navigate to="/security-setup" replace />;

  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <header className="sticky top-0 z-10 bg-surface-elevated border-b border-border shadow-card">
        <nav className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-14 items-center justify-between">
            <NavLink
              to="/"
              className="text-lg font-semibold text-ink no-underline hover:text-accent transition-colors duration-200"
            >
              Syllabify
            </NavLink>
            <div className="flex items-center gap-1">
              <ThemeToggle />
              {navItems.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `rounded-button px-3 py-2 text-sm font-medium no-underline transition-colors duration-200 ${
                      isActive
                        ? 'bg-accent-muted text-accent'
                        : 'text-ink-muted hover:bg-surface-muted hover:text-ink'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
              <span className="ml-2 text-sm text-ink-muted px-2">
                {user.username}
              </span>
            <button
              type="button"
              onClick={logout}
              className="rounded-button bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors duration-200"
            >
                Log out
              </button>
            </div>
          </div>
        </nav>
      </header>
      <main className="flex-1 mx-auto w-full max-w-5xl px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
