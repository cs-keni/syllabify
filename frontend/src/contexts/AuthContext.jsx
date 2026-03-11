/**
 * Auth state and actions. Provides login, logout, security setup.
 * DISCLAIMER: Project structure may change. Functions may be added, removed, or
 * modified. This describes the general idea as of the current state.
 */
import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react';
import * as api from '../api/client';

const TOKEN_KEY = 'syllabify_token';

const AuthContext = createContext(null);

function buildUser(authData, profileData) {
  return {
    username: authData.username,
    is_admin: !!authData.is_admin,
    avatar: profileData?.avatar || null,
    avatar_url: profileData?.avatar_url || null,
  };
}

/** Wraps the app to provide auth state. Loads user from token on mount. */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [securitySetupDone, setSecuritySetupDone] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  /** Fetches current user from API using token. Returns auth payload if valid. */
  const loadUser = useCallback(async t => {
    try {
      const authData = await api.me(t);
      if (authData) {
        const profileData = await api.getProfile(t);
        setUser(buildUser(authData, profileData));
        setSecuritySetupDone(!!authData.security_setup_done);
        return authData;
      }
      return null;
    } catch {
      return null;
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const t = token || localStorage.getItem(TOKEN_KEY);
    if (!t) return false;
    const authData = await loadUser(t);
    return !!authData;
  }, [loadUser, token]);

  useEffect(() => {
    const onUnauthorized = () => {
      setToken(null);
      setUser(null);
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = '/login?expired=1';
    };
    window.addEventListener('auth:unauthorized', onUnauthorized);
    return () =>
      window.removeEventListener('auth:unauthorized', onUnauthorized);
  }, []);

  useEffect(() => {
    const t = localStorage.getItem(TOKEN_KEY);
    if (!t) {
      setIsLoading(false);
      return;
    }
    setToken(t);
    loadUser(t)
      .then(authData => {
        if (!authData) {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
          setSecuritySetupDone(true);
        }
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [loadUser]);

  /** Calls API login, stores token, updates state. Returns { security_setup_done }. */
  const login = useCallback(
    async (username, password) => {
      const data = await api.login(username, password);
      const t = data.token;
      localStorage.setItem(TOKEN_KEY, t);
      setToken(t);
      await loadUser(t);
      return { security_setup_done: !!data.security_setup_done };
    },
    [loadUser]
  );

  /** Calls API loginWithGoogle, stores token, updates state. Returns { security_setup_done }. */
  const loginWithGoogle = useCallback(
    async idToken => {
      const data = await api.loginWithGoogle(idToken);
      const t = data.token;
      localStorage.setItem(TOKEN_KEY, t);
      setToken(t);
      await loadUser(t);
      return { security_setup_done: !!data.security_setup_done };
    },
    [loadUser]
  );

  /** Clears token and user from storage and state. */
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setSecuritySetupDone(true);
  }, []);

  /** Sends security questions to API, marks setup complete. */
  const completeSecuritySetup = useCallback(
    async questions => {
      const t = token || localStorage.getItem(TOKEN_KEY);
      if (!t) return;
      await api.securitySetup(t, questions);
      setSecuritySetupDone(true);
    },
    [token]
  );

  const value = {
    user,
    token,
    securitySetupDone,
    isLoading,
    login,
    loginWithGoogle,
    logout,
    completeSecuritySetup,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Hook to access auth state and actions. Must be used within AuthProvider. */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
