/**
 * App shell: nav bar + main content. Requires auth; redirects to Login or SecuritySetup.
 * Nav uses a sliding indicator that moves between tabs with distance-based bounce animation.
 */
import { useRef, useLayoutEffect, useState, useEffect } from 'react';
import {
  Outlet,
  NavLink,
  Navigate,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ThemeToggle from './ThemeToggle';
import ShortcutsOverlay from './ShortcutsOverlay';

const navItems = [
  { to: '/app', label: 'Dashboard', end: true },
  { to: '/app/upload', label: 'Upload syllabus', end: true },
  { to: '/app/schedule', label: 'Schedule', end: true },
  { to: '/app/preferences', label: 'Preferences', end: true },
  { to: '/app/admin', label: 'Admin', end: true, adminOnly: true },
];

function getActiveIndex(pathname, items) {
  const idx = items.findIndex(item =>
    item.end
      ? pathname === item.to || pathname === item.to + '/'
      : pathname.startsWith(item.to)
  );
  return idx >= 0 ? idx : 0;
}

/** Cubic-bezier with overshoot: bouncy settle. More distance = stronger bounce. */
function getEasing(distance) {
  const overshoot = Math.min(1.4 + distance * 0.12, 1.85);
  return `cubic-bezier(0.34, ${overshoot}, 0.64, 1)`;
}

/** Main layout with header nav and Outlet for child routes. */
export default function Layout() {
  const { user, securitySetupDone, logout } = useAuth();
  const location = useLocation();
  const navContainerRef = useRef(null);
  const linkRefs = useRef([]);
  const prevIndexRef = useRef(null);

  const [indicator, setIndicator] = useState({
    left: 0,
    top: 0,
    width: 0,
    height: 0,
  });
  const [transition, setTransition] = useState('none');
  const [mounted, setMounted] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [offline, setOffline] = useState(
    typeof navigator !== 'undefined' && !navigator.onLine
  );
  const profileRef = useRef(null);
  const navigate = useNavigate();

  const pathname = location.pathname;

  useEffect(() => {
    const onOnline = () => setOffline(false);
    const onOffline = () => setOffline(true);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);

  const gPendingRef = useRef(false);
  useEffect(() => {
    const onKey = e => {
      const inInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(
        document.activeElement?.tagName
      );
      if (inInput || e.ctrlKey || e.metaKey || e.altKey) {
        gPendingRef.current = false;
        return;
      }
      if (e.key === '?') {
        e.preventDefault();
        setShortcutsOpen(open => !open);
        gPendingRef.current = false;
        return;
      }
      if (gPendingRef.current) {
        gPendingRef.current = false;
        if (e.key === 'd') navigate('/app');
        else if (e.key === 'u') navigate('/app/upload');
        else if (e.key === 's') navigate('/app/schedule');
        else if (e.key === 'p') navigate('/app/preferences');
        return;
      }
      if (e.key === 'g') gPendingRef.current = true;
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [navigate]);

  useEffect(() => {
    if (!profileOpen) return;
    const onClickOutside = e => {
      if (profileRef.current && !profileRef.current.contains(e.target))
        setProfileOpen(false);
    };
    const onEscape = e => {
      if (e.key === 'Escape') setProfileOpen(false);
    };
    document.addEventListener('click', onClickOutside);
    document.addEventListener('keydown', onEscape);
    return () => {
      document.removeEventListener('click', onClickOutside);
      document.removeEventListener('keydown', onEscape);
    };
  }, [profileOpen]);

  const initials = user?.username
    ? user.username
        .slice(0, 2)
        .toUpperCase()
        .replace(/[^A-Z0-9]/g, '') || '?'
    : '?';
  const navItemsFiltered = navItems.filter(
    item => !item.adminOnly || user?.is_admin
  );
  const activeIndex = getActiveIndex(pathname, navItemsFiltered);

  useLayoutEffect(() => {
    const container = navContainerRef.current;
    const link = linkRefs.current[activeIndex];
    if (!container || !link) return;

    const containerRect = container.getBoundingClientRect();
    const linkRect = link.getBoundingClientRect();

    setMounted(true);

    const prevIndex = prevIndexRef.current;
    const distance = prevIndex !== null ? Math.abs(activeIndex - prevIndex) : 0;
    prevIndexRef.current = activeIndex;

    // Distance-based: longer = more duration, stronger bounce
    const duration = 150 + distance * 50;
    const easing = getEasing(distance);
    const isReduced = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches;
    const transitionValue = isReduced
      ? 'none'
      : `left ${duration}ms ${easing}, width ${duration}ms ${easing}, top ${duration}ms ${easing}, height ${duration}ms ${easing}`;

    setTransition(transitionValue);
    setIndicator({
      left: linkRect.left - containerRect.left,
      top: linkRect.top - containerRect.top,
      width: linkRect.width,
      height: linkRect.height,
    });
  }, [pathname, activeIndex]);

  useLayoutEffect(() => {
    const container = navContainerRef.current;
    if (!container) return;

    const ro = new ResizeObserver(() => {
      const link = linkRefs.current[activeIndex];
      if (!link) return;
      const containerRect = container.getBoundingClientRect();
      const linkRect = link.getBoundingClientRect();
      setIndicator({
        left: linkRect.left - containerRect.left,
        top: linkRect.top - containerRect.top,
        width: linkRect.width,
        height: linkRect.height,
      });
    });

    ro.observe(container);
    return () => ro.disconnect();
  }, [pathname, activeIndex]);

  if (!user) return <Navigate to="/login" replace />;
  if (!securitySetupDone) return <Navigate to="/security-setup" replace />;

  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <a
        href="#main-content"
        className="absolute -top-12 left-4 z-[100] rounded-button bg-accent px-4 py-2 text-sm font-medium text-white no-underline opacity-0 transition-opacity focus:top-4 focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-offset-2"
      >
        Skip to main content
      </a>
      {offline && (
        <div
          className="bg-amber-500 text-amber-950 text-sm text-center py-1.5 px-4 font-medium"
          role="status"
        >
          You're offline. Some features may not work.
        </div>
      )}
      <ShortcutsOverlay
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
      <header className="sticky top-0 z-10 bg-surface-elevated border-b border-border shadow-card">
        <nav className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="flex min-h-14 flex-wrap items-center gap-2 py-2 md:flex-nowrap md:justify-between md:py-0">
            <NavLink
              to="/"
              className="order-1 text-lg font-semibold text-ink no-underline hover:text-accent transition-colors duration-200"
            >
              Syllabify
            </NavLink>
            <div
              ref={navContainerRef}
              className="relative order-3 flex basis-full items-center gap-1 overflow-x-auto pb-1 md:order-2 md:basis-auto md:pb-0"
            >
              {mounted && (
                <div
                  className="absolute rounded-button bg-accent-muted -z-[1]"
                  style={{
                    left: indicator.left,
                    top: indicator.top,
                    width: indicator.width,
                    height: indicator.height,
                    transition,
                  }}
                  aria-hidden
                />
              )}
              {navItemsFiltered.map(({ to, label, end }, i) => (
                <NavLink
                  key={to}
                  ref={el => {
                    linkRefs.current[i] = el;
                  }}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `whitespace-nowrap rounded-button px-3 py-2.5 text-sm font-medium no-underline transition-colors duration-200 ${
                      isActive
                        ? 'text-accent'
                        : 'text-ink-muted hover:bg-surface-muted hover:text-ink'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>
            <div className="order-2 ml-auto flex items-center gap-2 md:order-3 md:ml-0">
              <button
                type="button"
                onClick={() => setShortcutsOpen(true)}
                className="rounded-button px-2 py-1 text-xs text-ink-subtle hover:text-ink hover:bg-surface-muted"
                title="Keyboard shortcuts (?)"
                aria-label="Show keyboard shortcuts"
              >
                ?
              </button>
              <ThemeToggle />
              <div className="relative" ref={profileRef}>
                <button
                  type="button"
                  onClick={e => {
                    e.stopPropagation();
                    setProfileOpen(open => !open);
                  }}
                  className="flex items-center gap-2 rounded-button px-2 py-1.5 text-sm text-ink-muted hover:bg-surface-muted hover:text-ink transition-colors"
                  aria-expanded={profileOpen}
                  aria-haspopup="menu"
                >
                  <span
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-muted text-accent text-xs font-medium shrink-0"
                    aria-hidden
                  >
                    {initials}
                  </span>
                  <span className="hidden sm:inline">{user.username}</span>
                  <svg
                    className={`h-4 w-4 shrink-0 transition-transform ${profileOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
                {profileOpen && (
                  <div
                    className="absolute right-0 mt-1 py-1 min-w-[160px] rounded-card border border-border bg-surface-elevated shadow-dropdown z-50 animate-fade-in"
                    role="menu"
                  >
                    <NavLink
                      to="/app/preferences"
                      onClick={() => setProfileOpen(false)}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-ink no-underline hover:bg-surface-muted rounded-t"
                      role="menuitem"
                    >
                      <svg
                        className="h-4 w-4 text-ink-subtle"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                      </svg>
                      Preferences
                    </NavLink>
                    <button
                      type="button"
                      onClick={() => {
                        setProfileOpen(false);
                        logout();
                      }}
                      className="flex w-full items-center gap-2 px-4 py-2 text-sm text-ink hover:bg-surface-muted rounded-b text-left"
                      role="menuitem"
                    >
                      <svg
                        className="h-4 w-4 text-ink-subtle"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                        />
                      </svg>
                      Log out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </nav>
      </header>
      <main
        id="main-content"
        className="flex-1 mx-auto w-full max-w-5xl px-4 sm:px-6 lg:px-8 py-6 sm:py-8"
      >
        <Outlet />
      </main>
    </div>
  );
}
