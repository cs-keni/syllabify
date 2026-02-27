/**
 * Full-page maintenance view. Shown when maintenance is on and user is not admin.
 */
import { useEffect, useState } from 'react';
import { getMaintenance } from '../api/client';
import ThemeToggle from '../components/ThemeToggle';

export default function MaintenancePage() {
  const [maintenance, setMaintenance] = useState({
    enabled: true,
    message: '',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMaintenance()
      .then(d => setMaintenance(d))
      .catch(() =>
        setMaintenance({ enabled: true, message: 'Please try again later.' })
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-surface text-ink flex items-center justify-center">
        <p className="text-ink-muted animate-pulse">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface text-ink flex flex-col">
      <header className="border-b border-border bg-surface-elevated py-4 px-6 flex justify-between items-center">
        <span className="text-lg font-semibold text-ink">Syllabify</span>
        <ThemeToggle />
      </header>
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="max-w-md text-center">
          <div
            className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 mb-6"
            aria-hidden
          >
            <svg
              className="w-8 h-8"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-ink mb-2">
            Under maintenance
          </h1>
          <p className="text-ink-muted">
            {maintenance.message ||
              'Syllabify is undergoing maintenance. Please try again later.'}
          </p>
          <p className="mt-6 text-sm text-ink-subtle">
            Please check back soon. Admins can continue to access the app.
          </p>
        </div>
      </main>
    </div>
  );
}
