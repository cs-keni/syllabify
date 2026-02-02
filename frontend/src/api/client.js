/**
 * API client: base URL from env, auth token in headers.
 * Methods: login, securitySetup, me. Used by useAuth and pages.
 *
 * DISCLAIMER: Project structure may change. Functions may be added, removed, or
 * modified. This describes the general idea as of the current state.
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';

/** Returns fetch headers. If withAuth and token provided, adds Authorization: Bearer. */
function headers(withAuth = false, token = null) {
  const h = { 'Content-Type': 'application/json' };
  const t =
    token ||
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (withAuth && t) h['Authorization'] = `Bearer ${t}`;
  return h;
}

/** POST to /api/auth/login. Returns { token, username, security_setup_done }. Throws on error. */
export async function login(username, password) {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST',
    headers: headers(false),
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Login failed');
  return data;
}

/** POST to /api/auth/security-setup with JWT. Saves security Q&A. Throws on error. */
export async function securitySetup(token, questions) {
  const res = await fetch(`${BASE}/api/auth/security-setup`, {
    method: 'POST',
    headers: headers(true, token),
    body: JSON.stringify({ questions }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Security setup failed');
  return data;
}

/** GET /api/auth/me with JWT. Returns { username, security_setup_done } or null if invalid. */
export async function me(token) {
  const t =
    token ||
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (!t) return null;
  const res = await fetch(`${BASE}/api/auth/me`, {
    headers: headers(true, t),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return null;
  return data;
}

export default { login, securitySetup, me };
