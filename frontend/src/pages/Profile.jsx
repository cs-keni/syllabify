/**
 * Profile page. Placeholder for custom profile pictures, descriptions, banners.
 * TODO: Add avatar upload (including GIF support), description, banner.
 */
import { useAuth } from '../contexts/AuthContext';
import { Link } from 'react-router-dom';

export default function Profile() {
  const { user } = useAuth();
  const initials = user?.username
    ? user.username
        .slice(0, 2)
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, '') || '?'
    : '?';

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <Link
          to="/app"
          className="text-sm text-ink-muted hover:text-ink transition-colors no-underline"
        >
          &larr; Dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-ink">Profile</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Customize your profile picture, description, and banner.
        </p>
      </div>

      <div className="rounded-xl border border-border bg-surface-elevated p-6 shadow-card animate-fade-in [animation-delay:100ms]">
        <div className="flex flex-col sm:flex-row gap-6">
          <div className="shrink-0">
            <div
              className="w-24 h-24 rounded-full bg-accent-muted flex items-center justify-center text-accent text-2xl font-semibold"
              aria-hidden
            >
              {initials}
            </div>
            <p className="mt-2 text-xs text-ink-muted text-center">
              Profile picture coming soon
            </p>
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-medium text-ink mb-1">{user?.username}</h2>
            <p className="text-sm text-ink-muted">
              Custom profile pictures (including GIFs), descriptions, and banners
              will be available in a future update.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
