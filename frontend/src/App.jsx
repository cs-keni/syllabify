/**
 * Root app component. Sets up Router, AuthProvider, and routes.
 * DISCLAIMER: Project structure may change. Components/routes may be added or
 * modified. This describes the general idea as of the current state.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { AccentProvider } from './contexts/AccentContext';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Course from './pages/Course';
import Schedule from './pages/Schedule';
import Preferences from './pages/Preferences';
import Admin from './pages/Admin';
import Login from './pages/Login';
import Register from './pages/Register';
import SecuritySetup from './pages/SecuritySetup';
import Home from './pages/Homepage';
import MaintenancePage from './pages/MaintenancePage';
import { getMaintenance, getSettings } from './api/client';
import { useState, useEffect } from 'react';
import './styles/index.css';

/** Shown while auth is loading. */
function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <p className="text-ink-muted animate-fade-in">Loading…</p>
    </div>
  );
}

/** Site-wide announcement banner from admin. */
function AnnouncementBanner() {
  const [announcement, setAnnouncement] = useState('');

  useEffect(() => {
    getSettings()
      .then(s => setAnnouncement(s.announcement || ''))
      .catch(() => setAnnouncement(''));
  }, []);

  if (!announcement.trim()) return null;
  return (
    <div
      className="bg-indigo-600 text-white text-center py-2 px-4 text-sm font-medium"
      role="status"
    >
      {announcement}
    </div>
  );
}

/** When maintenance is on and user is not admin, shows maintenance page. */
function MaintenanceGuard({ children }) {
  const { user, isLoading } = useAuth();
  const [maintenance, setMaintenance] = useState(null);

  useEffect(() => {
    getMaintenance()
      .then(d => setMaintenance(d))
      .catch(() => setMaintenance({ enabled: false, message: '' }));
  }, []);

  if (maintenance === null) return <Loading />;
  if (maintenance.enabled && !user?.is_admin) return <MaintenancePage />;
  return children;
}

/** Renders all routes. Waits for auth to load before showing content. */
function AppRoutes() {
  const { isLoading } = useAuth();
  if (isLoading) return <Loading />;
  return (
    <MaintenanceGuard>
      <AnnouncementBanner />
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/security-setup" element={<SecuritySetup />} />
          {/* Redirect legacy paths (old nav used /upload, /schedule, /preferences) */}
          <Route
            path="/upload"
            element={<Navigate to="/app/upload" replace />}
          />
          <Route
            path="/schedule"
            element={<Navigate to="/app/schedule" replace />}
          />
          <Route
            path="/preferences"
            element={<Navigate to="/app/preferences" replace />}
          />
          <Route path="/app" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<Upload />} />
            <Route path="courses/:courseId" element={<Course />} />
            <Route path="schedule" element={<Schedule />} />
            <Route path="preferences" element={<Preferences />} />
            <Route path="admin" element={<Admin />} />
            <Route path="*" element={<Navigate to="/app" replace />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </MaintenanceGuard>
  );
}

/** Root component: wraps app in Router, ThemeProvider, and AuthProvider. */
export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AccentProvider>
          <AuthProvider>
            <AppRoutes />
            <span
              className="fixed bottom-2 right-2 text-[10px] text-ink-muted/60 font-mono select-none pointer-events-none z-[5]"
              title={
                typeof __BUILD_DATE__ !== 'undefined'
                  ? `Built ${__BUILD_DATE__}`
                  : undefined
              }
            >
              v{typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '?'}
            </span>
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 3000,
                style: {
                  background: 'var(--color-surface-elevated)',
                  color: 'var(--color-ink)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-card)',
                },
                success: {
                  iconTheme: {
                    primary: 'var(--color-accent)',
                    secondary: 'var(--color-surface)',
                  },
                },
              }}
            />
          </AuthProvider>
        </AccentProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
