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
const AVATAR_MAP_KEY = 'syllabify_avatar_map';

function getAvatarMap() {
  try {
    return JSON.parse(localStorage.getItem(AVATAR_MAP_KEY) || '{}');
  } catch {
    return {};
  }
}

function getAvatarForUsername(username) {
  if (!username) return null;
  const map = getAvatarMap();
  return map[username] || null;
}

function setAvatarForUsername(username, avatar) {
  if (!username) return;
  const map = getAvatarMap();
  if (avatar) map[username] = avatar;
  else delete map[username];
  localStorage.setItem(AVATAR_MAP_KEY, JSON.stringify(map));
}

const AuthContext = createContext(null);

/** Wraps the app to provide auth state. Loads user from token on mount. */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [securitySetupDone, setSecuritySetupDone] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  /** Fetches current user from API using token. Returns true if valid. */
  const loadUser = useCallback(async t => {
    try {
      const data = await api.me(t);
      if (data) {
        setUser({
          username: data.username,
          is_admin: !!data.is_admin,
          avatar_key: getAvatarForUsername(data.username),
        });
        setSecuritySetupDone(!!data.security_setup_done);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

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
      .then(ok => {
        if (!ok) {
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
  const login = useCallback(async (username, password) => {
    const data = await api.login(username, password);
    const t = data.token;
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setUser({
      username: data.username,
      is_admin: !!data.is_admin,
      avatar_key: getAvatarForUsername(data.username),
    });
    setSecuritySetupDone(!!data.security_setup_done);
    return { security_setup_done: !!data.security_setup_done };
  }, []);

  /** Calls API loginWithGoogle, stores token, updates state. Returns { security_setup_done }. */
  const loginWithGoogle = useCallback(async idToken => {
    const data = await api.loginWithGoogle(idToken);
    const t = data.token;
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setUser({
      username: data.username,
      is_admin: !!data.is_admin,
      avatar_key: getAvatarForUsername(data.username),
    });
    setSecuritySetupDone(!!data.security_setup_done);
    return { security_setup_done: !!data.security_setup_done };
  }, []);

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

  const setAvatar = useCallback(avatarKey => {
    setUser(prev => {
      if (!prev?.username) return prev;
      setAvatarForUsername(prev.username, avatarKey);
      return { ...prev, avatar_key: avatarKey || null };
    });
  }, []);

  const value = {
    user,
    token,
    securitySetupDone,
    isLoading,
    login,
    loginWithGoogle,
    logout,
    completeSecuritySetup,
    setAvatar,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Hook to access auth state and actions. Must be used within AuthProvider. */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
