/**
 * Root app component. Sets up Router, AuthProvider, and routes.
 * DISCLAIMER: Project structure may change. Components/routes may be added or
 * modified. This describes the general idea as of the current state.
 */
import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Schedule from './pages/Schedule';
import Preferences from './pages/Preferences';
import Login from './pages/Login';
import SecuritySetup from './pages/SecuritySetup';
import Home from './pages/Homepage';
import SplashScreen from './components/SplashScreen';
import './styles/index.css';

/** Renders all routes. Splash on first load, fades to content when auth ready. */
function AppRoutes() {
  const { isLoading } = useAuth();
  const [splashState, setSplashState] = useState('visible'); // 'visible' | 'exiting' | 'hidden'

  useEffect(() => {
    if (!isLoading && splashState === 'visible') {
      setSplashState('exiting');
    }
  }, [isLoading, splashState]);

  const handleSplashTransitionEnd = () => setSplashState('hidden');
  const showSplash = splashState === 'visible' || splashState === 'exiting';

  return (
    <>
      {showSplash && (
        <SplashScreen
          exiting={splashState === 'exiting'}
          onTransitionEnd={handleSplashTransitionEnd}
        />
      )}
      {!isLoading && (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/security-setup" element={<SecuritySetup />} />
      {/* Redirect legacy paths (old nav used /upload, /schedule, /preferences) */}
      <Route path="/upload" element={<Navigate to="/app/upload" replace />} />
      <Route path="/schedule" element={<Navigate to="/app/schedule" replace />} />
      <Route path="/preferences" element={<Navigate to="/app/preferences" replace />} />
      <Route path="/app" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<Upload />} />
        <Route path="schedule" element={<Schedule />} />
        <Route path="preferences" element={<Preferences />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Route>
    </Routes>
      )}
    </>
  );
}

/** Root component: wraps app in Router, ThemeProvider, and AuthProvider. */
export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
