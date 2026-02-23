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
 * Create course under active term and add assignments.
 * Body: { course_name, assignments: [{ name, due?, hours? }] }.
 * Returns { id, course_name }.
 * termId optional: if omitted, fetches terms and uses the active one.
 */
export async function saveCourse(token, termIdOrPayload, maybePayload) {
  let termId;
  let payload;
  if (typeof termIdOrPayload === 'object') {
    payload = termIdOrPayload;
    const termsRes = await fetch(`${BASE}/api/terms`, {
      headers: headers(true),
      credentials: 'include',
    });
    const termsData = await termsRes.json().catch(() => ({}));
    if (!termsRes.ok)
      throw new Error(termsData.error || 'Failed to fetch terms');
    const terms = termsData.terms || [];
    const active = terms.find(t => t.is_active) || terms[0];
    if (!active) throw new Error('No term found. Create a term first.');
    termId = active.id;
  } else {
    termId = termIdOrPayload;
    payload = maybePayload;
  }
  const { course_name, assignments } = payload || {};
  const course = await createCourse(termId, course_name || 'Course');
  const items = (assignments || []).map(a => ({
    name: a.name,
    due: a.due || null,
    hours: a.hours ?? 3,
  }));
  if (items.length > 0) {
    await addAssignments(course.id, items);
  }
  return { id: course.id, course_name: course.course_name || course_name };
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

/** GET /api/terms. Returns { terms: [...] }. Throws on error. */
export async function getTerms() {
  const res = await fetch(`${BASE}/api/terms`, {
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to fetch terms');
  return data;
}

/** POST /api/terms. Creates new term. Returns { term: {...} }. Throws on error. */
export async function createTerm(termData) {
  const res = await fetch(`${BASE}/api/terms`, {
    method: 'POST',
    headers: headers(true),
    body: JSON.stringify(termData),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to create term');
  return data;
}

/** GET /api/terms/:id. Returns { term: {...} }. Throws on error. */
export async function getTerm(termId) {
  const res = await fetch(`${BASE}/api/terms/${termId}`, {
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to fetch term');
  return data;
}

/** PUT /api/terms/:id. Updates term. Returns { term: {...} }. Throws on error. */
export async function updateTerm(termId, termData) {
  const res = await fetch(`${BASE}/api/terms/${termId}`, {
    method: 'PUT',
    headers: headers(true),
    body: JSON.stringify(termData),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update term');
  return data;
}

/** DELETE /api/terms/:id. Deletes term. Returns { message: "..." }. Throws on error. */
export async function deleteTerm(termId) {
  const res = await fetch(`${BASE}/api/terms/${termId}`, {
    method: 'DELETE',
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to delete term');
  return data;
}

/** POST /api/terms/:id/activate. Sets term as active. Returns { term: {...} }. Throws on error. */
export async function activateTerm(termId) {
  const res = await fetch(`${BASE}/api/terms/${termId}/activate`, {
    method: 'POST',
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to activate term');
  return data;
}

/** GET /api/terms/:termId/courses. Returns { courses: [...] }. */
export async function getCourses(termId) {
  const res = await fetch(`${BASE}/api/terms/${termId}/courses`, {
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to fetch courses');
  return data;
}

/** POST /api/terms/:termId/courses. Returns { id, course_name, assignment_count }. */
export async function createCourse(termId, courseName) {
  const res = await fetch(`${BASE}/api/terms/${termId}/courses`, {
    method: 'POST',
    headers: headers(true),
    body: JSON.stringify({ course_name: courseName }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to create course');
  return data;
}

/** GET /api/courses/:courseId. Returns course with assignments array. */
export async function getCourse(courseId) {
  const res = await fetch(`${BASE}/api/courses/${courseId}`, {
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to fetch course');
  return data;
}

/** DELETE /api/courses/:courseId. Returns { ok: true }. */
export async function deleteCourse(courseId) {
  const res = await fetch(`${BASE}/api/courses/${courseId}`, {
    method: 'DELETE',
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to delete course');
  return data;
}

/** POST /api/courses/:courseId/assignments. Bulk-saves parsed assignments. */
export async function addAssignments(courseId, assignments) {
  const res = await fetch(`${BASE}/api/courses/${courseId}/assignments`, {
    method: 'POST',
    headers: headers(true),
    body: JSON.stringify({ assignments }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to save assignments');
  return data;
}

export default {
  login,
  securitySetup,
  me,
  getTerms,
  createTerm,
  getTerm,
  updateTerm,
  deleteTerm,
  activateTerm,
  getCourses,
  createCourse,
  getCourse,
  deleteCourse,
  addAssignments,
  parseSyllabus,
};
