/**
 * API client: base URL from env, auth token in headers.
 * Methods: login, securitySetup, me. Used by useAuth and pages.
 *
 * DISCLAIMER: Project structure may change. Functions may be added, removed, or
 * modified. This describes the general idea as of the current state.
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';

/** Like fetch but on 401 from authenticated API calls, clears token and dispatches auth:unauthorized. */
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, opts);
  const hadAuth =
    opts.headers && (opts.headers.Authorization || opts.headers.authorization);
  if (
    res.status === 401 &&
    hadAuth &&
    typeof url === 'string' &&
    url.includes('/api/')
  ) {
    try {
      localStorage.removeItem('syllabify_token');
      window.dispatchEvent(
        new CustomEvent('auth:unauthorized', {
          detail: { message: 'Session expired. Please sign in again.' },
        })
      );
    } catch (_) {
      // Ignore storage/event failures during forced logout handling.
    }
  }
  return res;
}

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

/** POST to /api/auth/register. Returns { id, username, security_setup_done }. Throws on error. */
export async function register(username, password) {
  const res = await apiFetch(`${BASE}/api/auth/register`, {
    method: 'POST',
    headers: headers(false),
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg =
      data.error === 'registration_closed'
        ? data.message || 'Signups are currently closed.'
        : data.error || 'Registration failed';
    throw new Error(msg);
  }
  return data;
}

/** POST to /api/auth/login. Returns { token, username, security_setup_done }. Throws on error. */
export async function login(username, password) {
  const res = await apiFetch(`${BASE}/api/auth/login`, {
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
  const res = await apiFetch(`${BASE}/api/auth/security-setup`, {
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

  const res = await apiFetch(url.toString(), {
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
    const termsRes = await apiFetch(`${BASE}/api/terms`, {
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
  const { course_name, assignments, meeting_times, study_hours_per_week } =
    payload || {};
  const course = await createCourse(
    termId,
    course_name || 'Course',
    study_hours_per_week
  );
  const items = (assignments || []).map(a => ({
    name: a.name,
    due: a.due || a.due_date || null,
    hours: a.hours ?? 3,
    type: a.type || 'assignment',
  }));
  if (items.length > 0) {
    await addAssignments(course.id, items);
  }
  if (Array.isArray(meeting_times) && meeting_times.length > 0) {
    await addMeetings(course.id, meeting_times);
  }
  return { id: course.id, course_name: course.course_name || course_name };
}

/** POST /api/courses/:courseId/meetings. Bulk-save meeting times (from parsed syllabus). */
export async function addMeetings(courseId, meeting_times) {
  const res = await apiFetch(`${BASE}/api/courses/${courseId}/meetings`, {
    method: 'POST',
    headers: headers(true),
    body: JSON.stringify({ meeting_times }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to save meeting times');
  return data;
}

/** GET /api/users/me with JWT. Returns { id, username, email, security_setup_done }. */
export async function getProfile(token) {
  const t =
    token ||
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (!t) return null;
  const res = await apiFetch(`${BASE}/api/users/me`, {
    headers: headers(true, t),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return null;
  return data;
}

/** GET /api/settings. Public. Returns { registration_open, announcement }. */
export async function getSettings() {
  const res = await apiFetch(`${BASE}/api/settings`, {
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  return {
    registration_open: data.registration_open !== false,
    announcement: data.announcement || '',
  };
}

/** GET /api/maintenance. Public. Returns { enabled, message }. */
export async function getMaintenance() {
  const res = await apiFetch(`${BASE}/api/maintenance`, {
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  return { enabled: !!data.enabled, message: data.message || '' };
}

/** GET /api/admin/settings. Admin only. Returns { registration_enabled, announcement }. */
export async function adminGetSettings(token) {
  const res = await apiFetch(`${BASE}/api/admin/settings`, {
    headers: headers(true, token),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to load settings');
  return data;
}

/** PUT /api/admin/settings. Body: { registration_enabled?, announcement? }. Admin only. */
export async function adminSetSettings(
  token,
  { registration_enabled, announcement }
) {
  const res = await apiFetch(`${BASE}/api/admin/settings`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify({
      ...(registration_enabled !== undefined && {
        registration_enabled: !!registration_enabled,
      }),
      ...(announcement !== undefined && { announcement: announcement || '' }),
    }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update settings');
  return data;
}

/** PUT /api/admin/maintenance. Body: { enabled, message }. Admin only. */
export async function adminSetMaintenance(token, { enabled, message }) {
  const res = await apiFetch(`${BASE}/api/admin/maintenance`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify({ enabled: !!enabled, message: message || '' }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update maintenance');
  return data;
}

/** GET /api/admin/audit-log. Admin only. Returns { entries: [...] }. */
export async function getAdminAuditLog(token, { limit = 50, offset = 0 } = {}) {
  const url = new URL(`${BASE}/api/admin/audit-log`);
  url.searchParams.set('limit', String(limit));
  url.searchParams.set('offset', String(offset));
  const res = await apiFetch(url.toString(), {
    headers: headers(true, token),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to load audit log');
  return data;
}

/** GET /api/admin/stats. Admin only. Returns aggregate counts. */
export async function getAdminStats(token) {
  const res = await apiFetch(`${BASE}/api/admin/stats`, {
    headers: headers(true, token),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to load stats');
  return data;
}

/** POST /api/admin/users with JWT. Admin only. Body: { username, password }. Returns { id, username }. */
export async function adminCreateUser(token, { username, password }) {
  const res = await apiFetch(`${BASE}/api/admin/users`, {
    method: 'POST',
    headers: headers(true, token),
    body: JSON.stringify({ username, password }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to create user');
  return data;
}

/** GET /api/admin/users/:id with JWT. Admin only. Returns user details + terms_count, courses_count, assignments_count. */
export async function getAdminUserDetails(token, userId) {
  const res = await apiFetch(`${BASE}/api/admin/users/${userId}`, {
    headers: headers(true, token),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to load user');
  return data;
}

/** GET /api/admin/users with JWT. Admin only. Returns { users: [...] }. */
export async function getAdminUsers(token) {
  const res = await apiFetch(`${BASE}/api/admin/users`, {
    headers: headers(true, token),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to load users');
  return data;
}

/** PUT /api/admin/users/:id/set-password. Body: { new_password }. Admin only. */
export async function adminSetPassword(token, userId, newPassword) {
  const res = await apiFetch(`${BASE}/api/admin/users/${userId}/set-password`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify({ new_password: newPassword }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to set password');
  return data;
}

/** PUT /api/admin/users/:id/disable. Body: { disabled }. Admin only. */
export async function disableUser(token, userId, disabled) {
  const res = await apiFetch(`${BASE}/api/admin/users/${userId}/disable`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify({ disabled: !!disabled }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update');
  return data;
}

/** PUT /api/admin/users/:id/reset-security. Admin only. */
export async function resetUserSecurity(token, userId) {
  const res = await apiFetch(
    `${BASE}/api/admin/users/${userId}/reset-security`,
    {
      method: 'PUT',
      headers: headers(true, token),
      body: JSON.stringify({}),
      credentials: 'include',
    }
  );
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to reset');
  return data;
}

/** DELETE /api/admin/users/:id. Body: { confirm: "DELETE" }. Admin only. */
export async function adminDeleteUser(token, userId) {
  const res = await apiFetch(`${BASE}/api/admin/users/${userId}`, {
    method: 'DELETE',
    headers: headers(true, token),
    body: JSON.stringify({ confirm: 'DELETE' }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok)
    throw new Error(data.error || data.message || 'Failed to delete');
  return data;
}

/** PUT /api/admin/users/:id/notes. Body: { note_text }. Admin only. */
export async function adminSetUserNotes(token, userId, noteText) {
  const res = await apiFetch(`${BASE}/api/admin/users/${userId}/notes`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify({ note_text: noteText || '' }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to save notes');
  return data;
}

/** PUT /api/admin/users/:id/set-admin. Body: { is_admin: true|false }. Admin only. */
export async function setAdminUser(token, userId, isAdmin) {
  const res = await apiFetch(`${BASE}/api/admin/users/${userId}/set-admin`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify({ is_admin: !!isAdmin }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update admin status');
  return data;
}

/** GET /api/users/me/preferences. Returns { work_start, work_end, preferred_days, max_hours_per_day }. */
export async function getPreferences(token) {
  const t =
    token ||
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (!t) return null;
  const res = await apiFetch(`${BASE}/api/users/me/preferences`, {
    headers: headers(true, t),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return null;
  return data;
}

/** PUT /api/users/me/preferences. Body: { work_start?, work_end?, preferred_days?, max_hours_per_day? }. */
export async function updatePreferences(token, prefs) {
  const res = await apiFetch(`${BASE}/api/users/me/preferences`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify(prefs),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to save preferences');
  return data;
}

/** POST /api/auth/change-password with JWT. Body: { current_password, new_password }. */
export async function changePassword(token, { currentPassword, newPassword }) {
  const res = await apiFetch(`${BASE}/api/auth/change-password`, {
    method: 'POST',
    headers: headers(true, token),
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to change password');
  return data;
}

/** PUT /api/users/me with JWT. Body: { email }. Returns updated profile. */
export async function updateProfile(token, { email }) {
  const res = await apiFetch(`${BASE}/api/users/me`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify({ email: email || null }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update profile');
  return data;
}

/** GET /api/auth/me with JWT. Returns { username, security_setup_done, is_admin } or null if invalid. */
export async function me(token) {
  const t =
    token ||
    (typeof localStorage !== 'undefined'
      ? localStorage.getItem('syllabify_token')
      : null);
  if (!t) return null;
  const res = await apiFetch(`${BASE}/api/auth/me`, {
    headers: headers(true, t),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return null;
  return data;
}

/** GET /api/terms. Returns { terms: [...] }. Throws on error. */
export async function getTerms() {
  const res = await apiFetch(`${BASE}/api/terms`, {
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to fetch terms');
  return data;
}

/** POST /api/terms. Creates new term. Returns { term: {...} }. Throws on error. */
export async function createTerm(termData) {
  const res = await apiFetch(`${BASE}/api/terms`, {
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
  const res = await apiFetch(`${BASE}/api/terms/${termId}`, {
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to fetch term');
  return data;
}

/** PUT /api/terms/:id. Updates term. Returns { term: {...} }. Throws on error. */
export async function updateTerm(termId, termData) {
  const res = await apiFetch(`${BASE}/api/terms/${termId}`, {
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
  const res = await apiFetch(`${BASE}/api/terms/${termId}`, {
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
  const res = await apiFetch(`${BASE}/api/terms/${termId}/activate`, {
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
  const res = await apiFetch(`${BASE}/api/terms/${termId}/courses`, {
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to fetch courses');
  return data;
}

/** POST /api/terms/:termId/courses. Returns { id, course_name, assignment_count }. */
export async function createCourse(
  termId,
  courseName,
  studyHoursPerWeek = null
) {
  const body = { course_name: courseName };
  if (studyHoursPerWeek != null && studyHoursPerWeek !== '')
    body.study_hours_per_week = studyHoursPerWeek;
  const res = await apiFetch(`${BASE}/api/terms/${termId}/courses`, {
    method: 'POST',
    headers: headers(true),
    body: JSON.stringify(body),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to create course');
  return data;
}

/** GET /api/courses/:courseId. Returns course with assignments array. */
export async function getCourse(courseId) {
  const res = await apiFetch(`${BASE}/api/courses/${courseId}`, {
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to fetch course');
  return data;
}

/**
 * PUT /api/courses/:courseId. Replace course assignments and meetings.
 * Body: { course_name?, study_hours_per_week?, assignments, meeting_times }.
 * Used when re-uploading syllabus from Course page.
 */
export async function updateCourse(token, courseId, payload) {
  const { course_name, assignments, meeting_times, study_hours_per_week } =
    payload || {};
  const body = {
    course_name: course_name || 'Course',
    assignments: Array.isArray(assignments) ? assignments : [],
    meeting_times: Array.isArray(meeting_times) ? meeting_times : [],
  };
  if (study_hours_per_week != null && study_hours_per_week !== '')
    body.study_hours_per_week = study_hours_per_week;
  const res = await apiFetch(`${BASE}/api/courses/${courseId}`, {
    method: 'PUT',
    headers: headers(true, token),
    body: JSON.stringify(body),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update course');
  return data;
}

/** PATCH /api/courses/:courseId. Partial update: { course_name?, color?, study_hours_per_week? }. */
export async function patchCourse(token, courseId, payload) {
  const res = await apiFetch(`${BASE}/api/courses/${courseId}`, {
    method: 'PATCH',
    headers: headers(true, token),
    body: JSON.stringify(payload || {}),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update course');
  return data;
}

/** DELETE /api/courses/:courseId. Returns { ok: true }. */
export async function deleteCourse(courseId) {
  const res = await apiFetch(`${BASE}/api/courses/${courseId}`, {
    method: 'DELETE',
    headers: headers(true),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to delete course');
  return data;
}

/** PATCH /api/assignments/:id. Body: { assignment_name?, due_date?, hours?, type? }. */
export async function updateAssignment(token, assignmentId, body) {
  const res = await apiFetch(`${BASE}/api/assignments/${assignmentId}`, {
    method: 'PATCH',
    headers: headers(true, token),
    body: JSON.stringify(body || {}),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to update assignment');
  return data;
}

/** DELETE /api/assignments/:id. */
export async function deleteAssignment(token, assignmentId) {
  const res = await apiFetch(`${BASE}/api/assignments/${assignmentId}`, {
    method: 'DELETE',
    headers: headers(true, token),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to delete assignment');
  return data;
}

/** POST /api/courses/:courseId/assignments. Bulk-saves parsed assignments. */
export async function addAssignments(courseId, assignments) {
  const res = await apiFetch(`${BASE}/api/courses/${courseId}/assignments`, {
    method: 'POST',
    headers: headers(true),
    body: JSON.stringify({ assignments }),
    credentials: 'include',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to save assignments');
  return data;
}

/** POST /api/schedule/terms/:termId/generate-study-times. Generates study time blocks for the term. Returns { ok, created_count, study_times }. */
export async function generateStudyTimes(token, termId) {
  const res = await apiFetch(
    `${BASE}/api/schedule/terms/${termId}/generate-study-times`,
    {
      method: 'POST',
      headers: headers(true, token),
      credentials: 'include',
    }
  );
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Failed to generate study times');
  return data;
}

export default {
  login,
  register,
  securitySetup,
  me,
  getProfile,
  updateProfile,
  getPreferences,
  updatePreferences,
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
  updateCourse,
  patchCourse,
  addAssignments,
  addMeetings,
  updateAssignment,
  deleteAssignment,
  parseSyllabus,
  generateStudyTimes,
};
