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

/**
 * POST /api/syllabus/parse with JWT.
 * Provide file (File) or text (string); mode optional (default "rule").
 * Returns { course_name, assignments: [{ name, due_date, hours }], confidence?, raw_text? }.
 * Throws on error.
 */
export async function parseSyllabus(token, { file, text, mode = 'rule' }) {
  const t =
    token ||
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (!t) throw new Error('Login required');

  const url = new URL(`${BASE}/api/syllabus/parse`);
  if (mode) url.searchParams.set('mode', mode);

  let body;
  let reqHeaders = { Authorization: `Bearer ${t}` };

  if (file) {
    const form = new FormData();
    form.append('file', file);
    body = form;
  } else if (text != null && text !== '') {
    reqHeaders['Content-Type'] = 'application/json';
    body = JSON.stringify({ text: String(text) });
  } else {
    throw new Error('provide file or text');
  }

  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: reqHeaders,
    body,
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Parse failed');
  return data;
}

/**
 * GET /api/courses with JWT.
 * Returns { courses: [{ id, name, assignment_count }] }.
 */
export async function getCourses(token) {
  const t =
    token ??
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (!t) throw new Error('Login required');
  const res = await fetch(`${BASE}/api/courses`, {
    headers: headers(true, t),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to load courses');
  return data;
}

/**
 * POST /api/courses with JWT. Save course + assignments after review.
 * Body: { course_name, assignments: [{ name, due?, hours? }] }.
 * Returns { id, course_name }.
 */
export async function saveCourse(token, { course_name, assignments }) {
  const t =
    token ??
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (!t) throw new Error('Login required');
  const body = {
    course_name: course_name || 'Course',
    assignments: (assignments || []).map(a => ({
      name: a.name,
      due: a.due || null,
      hours: a.hours ?? 3,
    })),
  };
  const res = await fetch(`${BASE}/api/courses`, {
    method: 'POST',
    headers: headers(true, t),
    body: JSON.stringify(body),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to save course');
  return data;
}

/**
 * DELETE /api/courses/:id with JWT.
 */
export async function deleteCourse(token, courseId) {
  const t =
    token ??
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (!t) throw new Error('Login required');
  const res = await fetch(`${BASE}/api/courses/${courseId}`, {
    method: 'DELETE',
    headers: headers(true, t),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to delete course');
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
