/**
 * App shell: nav bar + main content. Requires auth; redirects to Login or SecuritySetup.
 * Nav uses a sliding indicator that moves between tabs with distance-based bounce animation.
 */
import { useRef, useLayoutEffect, useState } from 'react';
import { Outlet, NavLink, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ThemeToggle from './ThemeToggle';

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

  const pathname = location.pathname;
  const navItemsFiltered = navItems.filter(item => !item.adminOnly || user?.is_admin);
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
            <div className="order-2 ml-auto flex items-center gap-1 md:order-3 md:ml-0">
              <ThemeToggle />
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
      <main className="flex-1 mx-auto w-full max-w-5xl px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}
