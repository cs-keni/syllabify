# Phase 2: Scheduling Logic Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate imported CalendarEvents into the scheduling engine so study blocks avoid conflicts, respect deadline anchors, survive regeneration when locked, and allow users to pin/drag/unlock study blocks.

**Architecture:** Four-layer enhancement — (1) scheduling_service.py reads CalendarEvents as busy intervals + reconciles deadline_markers with assignment due_dates + preserves locked StudyTimes, (2) a PATCH endpoint with server-side overlap validation, (3) api/client.js new methods, (4) Schedule.jsx wires drag/resize + popover unlock UI.

**Tech Stack:** Python/SQLAlchemy ORM (backend), Flask Blueprint (API), React + FullCalendar (frontend)

---

## Context: Current State

- `backend/app/services/scheduling_service.py` — greedy + max-flow scheduler; only uses `meeting_busy` from course meetings; deletes ALL StudyTimes before regenerating; never sets `assignment_id` / `course_id`.
- `backend/app/models/calendar_event.py` — CalendarEvent ORM; `event_kind` (`timed`/`all_day`/`deadline_marker`), `event_category`, `sync_status`, `start_time/end_time` (naive UTC), `start_date` (for deadline_markers), `is_locally_modified`, `local_start_time/local_end_time`.
- `backend/app/models/study_time.py` — `is_locked`, `assignment_id`, `course_id` fields exist (migration 012) but scheduler never sets them.
- `backend/app/api/schedule.py` — GET `/api/schedule/terms/<id>/study-times` exists; no PATCH endpoint.
- `frontend/src/api/client.js` — no `updateStudyTime` method.
- `frontend/src/pages/Schedule.jsx` — `onEventDrop`/`onEventResize` not wired; `onEventClick` not wired.
- `frontend/src/components/AppCalendar.jsx` — `onEventClick` prop accepted but only passed through; no popover.

---

## Task 1: Set assignment_id + course_id when creating StudyTimes

**Files:**

- Modify: `backend/app/services/scheduling_service.py` — greedy StudyTime creation (~line 248), global solver StudyTime creation (~line 555)
- Test: `backend/tests/test_scheduling_service.py`

**Step 1: Write failing test**

```python
# backend/tests/test_scheduling_service.py

def test_study_times_have_assignment_and_course_ids(db_session, sample_term):
    """StudyTimes created by scheduler must have assignment_id and course_id set."""
    created = generate_study_times(db_session, sample_term.id)
    assert len(created) > 0
    for st in created:
        assert st.assignment_id is not None, "assignment_id must be set"
        assert st.course_id is not None, "course_id must be set"
```

**Step 2: Run to confirm it fails**

```bash
docker compose exec -T backend python -m pytest tests/test_scheduling_service.py::test_study_times_have_assignment_and_course_ids -v
```

Expected: FAIL

**Step 3: Update greedy phase StudyTime creation (~line 248)**

```python
# Before:
st = StudyTime(
    start_time=start,
    end_time=end,
    term_id=term_id,
    notes=None,
)

# After:
st = StudyTime(
    start_time=start,
    end_time=end,
    term_id=term_id,
    notes=None,
    assignment_id=assignment.id,
    course_id=assignment.course_id,
)
```

**Step 4: Update global solver StudyTime creation (~line 555)**

```python
# Before:
st = StudyTime(
    start_time=s,
    end_time=e,
    term_id=term_id,
    notes=None,
)

# After:
st = StudyTime(
    start_time=s,
    end_time=e,
    term_id=term_id,
    notes=None,
    assignment_id=a.id,
    course_id=a.course_id,
)
```

**Step 5: Rebuild and run test**

```bash
docker compose up -d --build backend
docker compose exec -T backend python -m pytest tests/test_scheduling_service.py::test_study_times_have_assignment_and_course_ids -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/services/scheduling_service.py backend/tests/test_scheduling_service.py
git commit -m "feat: set assignment_id and course_id on StudyTimes during scheduling"
```

---

## Task 2: Load CalendarEvents as busy intervals

**Files:**

- Modify: `backend/app/services/scheduling_service.py` — top of `generate_study_times`
- Test: `backend/tests/test_scheduling_service.py`

**Step 1: Write failing test**

```python
# backend/tests/test_scheduling_service.py

def test_calendar_event_blocks_study_slot(db_session, sample_term, sample_user):
    """Active timed CalendarEvents must appear as busy intervals."""
    from app.models.calendar_event import CalendarEvent
    from app.models.calendar_source import CalendarSource
    from datetime import datetime

    src = CalendarSource(
        user_id=sample_user.id,
        source_type="ics_url",
        source_label="Test",
        feed_category="other",
    )
    db_session.add(src)
    db_session.flush()

    # Block 9am-5pm on a weekday within term
    block_start = datetime(2026, 1, 5, 9, 0)
    block_end   = datetime(2026, 1, 5, 17, 0)

    evt = CalendarEvent(
        user_id=sample_user.id,
        source_id=src.id,
        external_uid="test-block-event",
        instance_key="base",
        title="Blocked",
        event_kind="timed",
        sync_status="active",
        start_time=block_start,
        end_time=block_end,
    )
    db_session.add(evt)
    db_session.commit()

    created = generate_study_times(db_session, sample_term.id)
    for st in created:
        assert not (st.start_time < block_end and st.end_time > block_start), (
            f"StudyTime {st.start_time}-{st.end_time} overlaps blocked window"
        )
```

**Step 2: Run to confirm it fails**

```bash
docker compose exec -T backend python -m pytest tests/test_scheduling_service.py::test_calendar_event_blocks_study_slot -v
```

Expected: FAIL

**Step 3: Add import at top of scheduling_service.py**

```python
from app.models.calendar_event import CalendarEvent
```

**Step 4: In generate_study_times, after meeting_busy is built, add CalendarEvent query**

Place this block after the `meeting_busy = _merge_intervals(meeting_busy)` line:

```python
# --- CalendarEvents as additional busy intervals ---
user_id = term.user_id
cal_events = (
    session.query(CalendarEvent)
    .filter(
        CalendarEvent.user_id == user_id,
        CalendarEvent.event_kind == "timed",
        CalendarEvent.sync_status == "active",
        CalendarEvent.start_time.isnot(None),
        CalendarEvent.end_time.isnot(None),
    )
    .all()
)

calendar_busy: list[tuple[datetime, datetime]] = []
for evt in cal_events:
    s = evt.local_start_time if (evt.is_locally_modified and evt.local_start_time) else evt.start_time
    e = evt.local_end_time if (evt.is_locally_modified and evt.local_end_time) else evt.end_time
    if s and e:
        if s.tzinfo is None:
            s = s.replace(tzinfo=ZoneInfo("UTC"))
        if e.tzinfo is None:
            e = e.replace(tzinfo=ZoneInfo("UTC"))
        calendar_busy.append((s, e))

# Re-merge all base busy intervals
meeting_busy = _merge_intervals(meeting_busy + calendar_busy)
```

**Step 5: Rebuild and run tests**

```bash
docker compose up -d --build backend
docker compose exec -T backend python -m pytest tests/test_scheduling_service.py -v
```

Expected: All pass

**Step 6: Commit**

```bash
git add backend/app/services/scheduling_service.py backend/tests/test_scheduling_service.py
git commit -m "feat: use CalendarEvents as busy intervals in scheduling engine"
```

---

## Task 3: Deadline reconciliation — augment Assignment.due_date from deadline_marker CalendarEvents

**Design:** At schedule-generation time, query `CalendarEvent` rows where `event_kind='deadline_marker'` for this user. For each Assignment, attempt a fuzzy title match against these events. If a match is found and the imported deadline is **earlier** than the assignment's own `due_date`, use the imported date as the effective deadline for that assignment's scheduling window. **Does not write to the DB** — reconciliation is purely in-memory.

**Matching rules:**

- Normalize both strings: lowercase, strip common prefixes (`"due:"`, `"assignment:"`, `"hw:"`, etc.), strip trailing punctuation
- Match if one normalized string is a substring of the other
- Only consider CalendarEvents where `start_date` or `start_time` is within ±14 days of `assignment.due_date` (prevents false matches across terms)
- If multiple matches, pick the one with the closest date

**Reconciliation rule:**

- `effective_due_date = min(assignment.due_date, imported_deadline_date)`
- If no match found: `effective_due_date = assignment.due_date` (unchanged)

**Files:**

- Modify: `backend/app/services/scheduling_service.py`
- Test: `backend/tests/test_scheduling_service.py`

**Step 1: Write failing test**

```python
def test_deadline_reconciliation_uses_earlier_imported_date(db_session, sample_term, sample_user, sample_assignment):
    """If imported deadline_marker is earlier than assignment.due_date, use it."""
    from app.models.calendar_event import CalendarEvent
    from app.models.calendar_source import CalendarSource
    from datetime import datetime, date, timedelta

    src = CalendarSource(
        user_id=sample_user.id,
        source_type="ics_url",
        source_label="Canvas",
        feed_category="canvas",
    )
    db_session.add(src)
    db_session.flush()

    # Assignment due 2026-02-01; imported deadline 1 week earlier
    earlier_date = date(2026, 1, 25)
    evt = CalendarEvent(
        user_id=sample_user.id,
        source_id=src.id,
        external_uid="canvas-deadline-1",
        instance_key="base",
        title=f"Due: {sample_assignment.assignment_name}",  # matches by title
        event_kind="deadline_marker",
        event_category="assignment_deadline",
        sync_status="active",
        start_date=earlier_date,
    )
    db_session.add(evt)
    db_session.commit()

    created = generate_study_times(db_session, sample_term.id)
    # All study blocks for this assignment should end before the earlier_date
    import pytz
    cutoff = datetime.combine(earlier_date, __import__('datetime').time(23, 59, 59))
    assignment_blocks = [st for st in created if st.assignment_id == sample_assignment.id]
    assert len(assignment_blocks) > 0
    for st in assignment_blocks:
        st_end = st.end_time.replace(tzinfo=None) if st.end_time.tzinfo else st.end_time
        assert st_end <= cutoff, f"Study block {st_end} exceeds reconciled deadline {cutoff}"
```

**Step 2: Run to confirm it fails**

```bash
docker compose exec -T backend python -m pytest tests/test_scheduling_service.py::test_deadline_reconciliation_uses_earlier_imported_date -v
```

Expected: FAIL

**Step 3: Add helper function \_normalize_title in scheduling_service.py**

Add near the top of the file (after imports):

```python
import re as _re

def _normalize_title(s: str) -> str:
    """Normalize a title for fuzzy deadline matching: lowercase, strip common prefixes."""
    s = s.lower().strip()
    for prefix in ("due:", "assignment:", "hw:", "homework:", "project:", "quiz:", "exam:"):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    return _re.sub(r"[^\w\s]", "", s).strip()
```

**Step 4: Add helper function \_reconcile_deadlines**

```python
def _reconcile_deadlines(
    session,
    user_id: int,
    assignments: list,
) -> dict[int, datetime]:
    """
    Return a dict mapping assignment.id -> effective_due_date.
    If an imported deadline_marker matches an assignment and is earlier,
    use the imported date. Otherwise keep assignment.due_date.
    """
    from datetime import timedelta

    # Query all active deadline_markers for this user
    markers = (
        session.query(CalendarEvent)
        .filter(
            CalendarEvent.user_id == user_id,
            CalendarEvent.event_kind == "deadline_marker",
            CalendarEvent.sync_status == "active",
        )
        .all()
    )

    effective: dict[int, datetime] = {}
    for a in assignments:
        effective[a.id] = a.due_date

        norm_name = _normalize_title(a.assignment_name)
        best_match_dt = None
        best_delta = None

        for marker in markers:
            # Get marker date
            if marker.start_date:
                m_dt = datetime.combine(marker.start_date, time(23, 59, 59), tzinfo=ZoneInfo("UTC"))
            elif marker.start_time:
                m_dt = marker.start_time
                if m_dt.tzinfo is None:
                    m_dt = m_dt.replace(tzinfo=ZoneInfo("UTC"))
            else:
                continue

            # Check date proximity: ±14 days from assignment.due_date
            due = a.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=ZoneInfo("UTC"))
            if abs((m_dt - due).days) > 14:
                continue

            # Fuzzy title match
            norm_title = _normalize_title(marker.title or "")
            if norm_name and norm_title and (
                norm_name in norm_title or norm_title in norm_name
            ):
                delta = abs((m_dt - due).total_seconds())
                if best_delta is None or delta < best_delta:
                    best_match_dt = m_dt
                    best_delta = delta

        if best_match_dt is not None:
            due = a.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=ZoneInfo("UTC"))
            # Only use imported date if it is earlier (more conservative)
            if best_match_dt < due:
                effective[a.id] = best_match_dt

    return effective
```

**Step 5: Call \_reconcile_deadlines in generate_study_times**

After the CalendarEvents busy interval block (Task 2), add:

```python
# --- Deadline reconciliation ---
effective_due_dates = _reconcile_deadlines(session, user_id, assignments)
```

Then in the greedy phase, replace `assignment.due_date` with `effective_due_dates[assignment.id]`:

```python
# Replace:
window_end = assignment.due_date
# With:
window_end = effective_due_dates.get(assignment.id, assignment.due_date)
```

Do the same replacement in the slack pre-computation loop and in `_generate_study_times_global` (pass `effective_due_dates` as a parameter).

**Step 6: Update \_generate_study_times_global signature**

```python
def _generate_study_times_global(
    session: Session,
    term: Term,
    assignments: list,
    meeting_busy: list[tuple[datetime, datetime]],
    tz: ZoneInfo,
    start_time: time,
    end_time: time,
    term_id: int,
    effective_due_dates: dict[int, datetime] | None = None,  # NEW
) -> list[StudyTime]:
```

Inside, replace `we` (window_end) with `effective_due_dates.get(a.id, we)` when building `normalized_assignments`.

**Step 7: Rebuild and run tests**

```bash
docker compose up -d --build backend
docker compose exec -T backend python -m pytest tests/test_scheduling_service.py -v
```

Expected: All pass

**Step 8: Commit**

```bash
git add backend/app/services/scheduling_service.py backend/tests/test_scheduling_service.py
git commit -m "feat: reconcile assignment due_dates from imported deadline_marker CalendarEvents"
```

---

## Task 4: Preserve locked StudyTimes during regeneration

**Files:**

- Modify: `backend/app/services/scheduling_service.py`
- Test: `backend/tests/test_scheduling_service.py`

**Step 1: Write failing test**

```python
def test_locked_study_times_survive_regeneration(db_session, sample_term):
    """Locked StudyTimes must not be deleted when regenerating."""
    from app.models.study_time import StudyTime
    from datetime import datetime

    locked_st = StudyTime(
        term_id=sample_term.id,
        start_time=datetime(2026, 1, 5, 8, 0),
        end_time=datetime(2026, 1, 5, 8, 15),
        is_locked=True,
    )
    db_session.add(locked_st)
    db_session.commit()
    locked_id = locked_st.id

    generate_study_times(db_session, sample_term.id)
    db_session.commit()

    still_exists = db_session.query(StudyTime).filter_by(id=locked_id).first()
    assert still_exists is not None, "Locked study time was deleted during regeneration"
    assert still_exists.is_locked is True


def test_new_study_times_do_not_overlap_locked(db_session, sample_term):
    """Newly generated StudyTimes must not overlap existing locked ones."""
    from app.models.study_time import StudyTime
    from datetime import datetime

    locked_st = StudyTime(
        term_id=sample_term.id,
        start_time=datetime(2026, 1, 5, 9, 0),
        end_time=datetime(2026, 1, 5, 9, 15),
        is_locked=True,
    )
    db_session.add(locked_st)
    db_session.commit()

    created = generate_study_times(db_session, sample_term.id)
    lock_s = datetime(2026, 1, 5, 9, 0)
    lock_e = datetime(2026, 1, 5, 9, 15)
    for st in created:
        assert not (st.start_time < lock_e and st.end_time > lock_s), (
            f"New StudyTime {st.start_time}-{st.end_time} overlaps locked block"
        )
```

**Step 2: Run to confirm they fail**

```bash
docker compose exec -T backend python -m pytest tests/test_scheduling_service.py::test_locked_study_times_survive_regeneration tests/test_scheduling_service.py::test_new_study_times_do_not_overlap_locked -v
```

Expected: FAIL

**Step 3: Modify the first delete in generate_study_times (~line 149)**

```python
# --- Load locked times BEFORE deletion ---
locked_study_times = (
    session.query(StudyTime)
    .filter(StudyTime.term_id == term_id, StudyTime.is_locked == True)
    .all()
)
# Delete only unlocked times
session.query(StudyTime).filter(
    StudyTime.term_id == term_id, StudyTime.is_locked == False
).delete(synchronize_session="fetch")

# Build locked busy intervals
locked_busy: list[tuple[datetime, datetime]] = []
for lst in locked_study_times:
    s = lst.start_time
    e = lst.end_time
    if s.tzinfo is None:
        s = s.replace(tzinfo=ZoneInfo("UTC"))
    if e.tzinfo is None:
        e = e.replace(tzinfo=ZoneInfo("UTC"))
    locked_busy.append((s, e))

# meeting_busy already contains calendar_busy from Task 2; add locked on top
meeting_busy = _merge_intervals(meeting_busy + locked_busy)
```

**Step 4: Fix the global fallback delete (~line 273)**

```python
# Before:
session.query(StudyTime).filter(StudyTime.term_id == term_id).delete()

# After:
session.query(StudyTime).filter(
    StudyTime.term_id == term_id, StudyTime.is_locked == False
).delete(synchronize_session="fetch")
```

**Step 5: Rebuild and run tests**

```bash
docker compose up -d --build backend
docker compose exec -T backend python -m pytest tests/test_scheduling_service.py -v
```

Expected: All pass

**Step 6: Commit**

```bash
git add backend/app/services/scheduling_service.py backend/tests/test_scheduling_service.py
git commit -m "feat: preserve locked StudyTimes during schedule regeneration"
```

---

## Task 5: Backend PATCH endpoint with server-side validation

**Validation rules (minimum MVP):**

1. `start_time < end_time` (time validity)
2. No overlap with `active` timed `CalendarEvents` for this user (excluding all-day)
3. No overlap with other `locked` StudyTimes in the same term (excluding self)

**Files:**

- Modify: `backend/app/api/schedule.py`
- Test: `backend/tests/test_schedule_api.py`

**Step 1: Write failing tests**

```python
# backend/tests/test_schedule_api.py

def test_patch_study_time_lock(client, auth_token, sample_study_time):
    resp = client.patch(
        f"/api/schedule/study-times/{sample_study_time.id}",
        json={"is_locked": True},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


def test_patch_study_time_invalid_times(client, auth_token, sample_study_time):
    """start >= end should be rejected."""
    resp = client.patch(
        f"/api/schedule/study-times/{sample_study_time.id}",
        json={"start_time": "2026-01-05T10:15:00", "end_time": "2026-01-05T10:00:00"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 422


def test_patch_study_time_overlaps_calendar_event(client, auth_token, sample_study_time, sample_calendar_event):
    """Move that overlaps an active timed CalendarEvent must be rejected."""
    resp = client.patch(
        f"/api/schedule/study-times/{sample_study_time.id}",
        json={
            "start_time": sample_calendar_event["start_time"],
            "end_time": sample_calendar_event["end_time"],
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 409


def test_patch_study_time_wrong_user(client, other_auth_token, sample_study_time):
    resp = client.patch(
        f"/api/schedule/study-times/{sample_study_time.id}",
        json={"is_locked": True},
        headers={"Authorization": f"Bearer {other_auth_token}"},
    )
    assert resp.status_code == 404
```

**Step 2: Run to confirm they fail**

```bash
docker compose exec -T backend python -m pytest tests/test_schedule_api.py -v 2>&1 | head -30
```

Expected: FAIL or 405

**Step 3: Add PATCH endpoint to schedule.py**

```python
@bp.route("/study-times/<int:study_time_id>", methods=["PATCH"])
def update_study_time(study_time_id):
    """
    PATCH /api/schedule/study-times/:id
    Fields: start_time, end_time, is_locked, notes.
    Validates: start < end; no overlap with active CalendarEvents or locked StudyTimes.
    """
    user_id, err = _get_user(request)
    if err:
        return err

    body = request.get_json() or {}
    conn = _get_db()
    try:
        cur = conn.cursor(dictionary=True)

        # Verify ownership
        cur.execute(
            """SELECT st.id, st.start_time, st.end_time, st.term_id
               FROM StudyTimes st
               JOIN Terms t ON st.term_id = t.id
               WHERE st.id = %s AND t.user_id = %s""",
            (study_time_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404

        new_start = body.get("start_time", str(row["start_time"]))
        new_end   = body.get("end_time",   str(row["end_time"]))
        term_id   = row["term_id"]

        # --- Validation ---
        from datetime import datetime as _dt
        try:
            s = _dt.fromisoformat(str(new_start).replace("Z", "+00:00"))
            e = _dt.fromisoformat(str(new_end).replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "invalid datetime format"}), 422

        if s >= e:
            return jsonify({"error": "start_time must be before end_time"}), 422

        # No overlap with active timed CalendarEvents
        cur.execute(
            """SELECT id, title FROM CalendarEvents
               WHERE user_id = %s
                 AND event_kind = 'timed'
                 AND sync_status = 'active'
                 AND start_time < %s
                 AND end_time   > %s
               LIMIT 1""",
            (user_id, str(e)[:19], str(s)[:19]),
        )
        conflict_evt = cur.fetchone()
        if conflict_evt:
            return jsonify({
                "error": "conflict",
                "message": f"Overlaps calendar event: {conflict_evt['title']}",
            }), 409

        # No overlap with OTHER locked StudyTimes in same term
        cur.execute(
            """SELECT id FROM StudyTimes
               WHERE term_id = %s
                 AND is_locked = 1
                 AND id != %s
                 AND start_time < %s
                 AND end_time   > %s
               LIMIT 1""",
            (term_id, study_time_id, str(e)[:19], str(s)[:19]),
        )
        if cur.fetchone():
            return jsonify({
                "error": "conflict",
                "message": "Overlaps another locked study block",
            }), 409

        # --- Apply update ---
        updates = []
        params = []
        if "start_time" in body:
            updates.append("start_time = %s")
            params.append(str(new_start)[:19])
        if "end_time" in body:
            updates.append("end_time = %s")
            params.append(str(new_end)[:19])
        if "is_locked" in body:
            updates.append("is_locked = %s")
            params.append(1 if body["is_locked"] else 0)
        if "notes" in body:
            updates.append("notes = %s")
            params.append(body["notes"])

        if not updates:
            return jsonify({"error": "no fields to update"}), 400

        params.append(study_time_id)
        cur.execute(
            f"UPDATE StudyTimes SET {', '.join(updates)} WHERE id = %s",
            params,
        )
        conn.commit()
        cur.close()
        return jsonify({"ok": True})
    finally:
        conn.close()
```

**Step 4: Rebuild and run tests**

```bash
docker compose up -d --build backend
docker compose exec -T backend python -m pytest tests/test_schedule_api.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/schedule.py backend/tests/test_schedule_api.py
git commit -m "feat: add PATCH /api/schedule/study-times/:id with overlap validation"
```

---

## Task 6: Add updateStudyTime to frontend API client

**Files:**

- Modify: `frontend/src/api/client.js`

**Step 1: Add function before `export default` block**

```javascript
/**
 * PATCH /api/schedule/study-times/:id.
 * Body: { start_time?, end_time?, is_locked?, notes? }.
 * Returns { ok: true } or throws with server error message.
 */
export async function updateStudyTime(token, studyTimeId, body) {
  const res = await apiFetch(
    `${BASE}/api/schedule/study-times/${studyTimeId}`,
    {
      method: "PATCH",
      headers: headers(true, token),
      body: JSON.stringify(body || {}),
      credentials: "include",
    },
  );
  const data = await res.json().catch(() => ({}));
  if (!res.ok)
    throw new Error(
      data.message || data.error || "Failed to update study time",
    );
  return data;
}
```

**Step 2: Add to export default object**

Add `updateStudyTime` to the list in the `export default { ... }` block.

**Step 3: Verify build**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: clean build

**Step 4: Commit**

```bash
git add frontend/src/api/client.js
git commit -m "feat: add updateStudyTime API client method"
```

---

## Task 7: Frontend — drag/resize auto-lock + popover with unlock

**Files:**

- Modify: `frontend/src/pages/Schedule.jsx`
- Modify: `frontend/src/components/AppCalendar.jsx` (add small StudyTimePopover)

### Part A — Drag/resize auto-lock

**Step 1: Add handler in Schedule.jsx after handleDeleteSource**

```javascript
const handleStudyTimeMove = async ({ props, start, end }) => {
  if (props.type !== "study_time") return;
  const studyTimeId = props.data.id;
  // Optimistic update
  setStudyTimes((prev) =>
    prev.map((st) =>
      st.id === studyTimeId
        ? {
            ...st,
            start_time: start.toISOString(),
            end_time: end.toISOString(),
            is_locked: true,
          }
        : st,
    ),
  );
  try {
    await api.updateStudyTime(token, studyTimeId, {
      start_time: start.toISOString().slice(0, 19).replace("T", " "),
      end_time: end.toISOString().slice(0, 19).replace("T", " "),
      is_locked: true,
    });
    toast.success("Study block pinned.");
  } catch (err) {
    toast.error(err.message || "Could not move study block");
    fetchData(); // Revert on error
  }
};
```

**Step 2: Wire props to AppCalendar**

```jsx
<AppCalendar
  calendarEvents={calendarEvents}
  studyTimes={studyTimes}
  onEventDrop={handleStudyTimeMove}
  onEventResize={handleStudyTimeMove}
  onEventClick={handleStudyTimeClick} // Added in Part B
/>
```

### Part B — Popover with Lock / Unlock

**Step 3: Add state and handler in Schedule.jsx**

```javascript
const [popover, setPopover] = useState(null); // { studyTime, x, y }

const handleStudyTimeClick = ({ type, data }, jsEvent) => {
  if (type !== "study_time") return;
  setPopover({
    studyTime: data,
    x: jsEvent?.clientX ?? 0,
    y: jsEvent?.clientY ?? 0,
  });
};

const handleToggleLock = async () => {
  if (!popover) return;
  const { studyTime } = popover;
  const newLocked = !studyTime.is_locked;
  setPopover(null);
  try {
    await api.updateStudyTime(token, studyTime.id, { is_locked: newLocked });
    setStudyTimes((prev) =>
      prev.map((st) =>
        st.id === studyTime.id ? { ...st, is_locked: newLocked } : st,
      ),
    );
    toast.success(newLocked ? "Study block locked." : "Study block unlocked.");
  } catch (err) {
    toast.error(err.message || "Failed to update");
    fetchData();
  }
};
```

**Step 4: Add popover JSX in Schedule.jsx return**

Place after the AppCalendar block:

```jsx
{
  popover && (
    <div
      className="fixed z-50 bg-white dark:bg-gray-800 border border-border rounded-lg shadow-lg p-3 text-sm min-w-[160px]"
      style={{ top: popover.y + 8, left: popover.x + 8 }}
    >
      <p className="font-medium text-ink mb-1 truncate">
        {popover.studyTime.course_name || "Study Block"}
      </p>
      <p className="text-xs text-ink-muted mb-2">
        {popover.studyTime.is_locked
          ? "Locked (pinned)"
          : "Unlocked (will regenerate)"}
      </p>
      <div className="flex gap-2">
        <button
          onClick={handleToggleLock}
          className="flex-1 text-xs rounded px-2 py-1 bg-primary text-primary-inv font-medium hover:opacity-90"
        >
          {popover.studyTime.is_locked ? "Unlock" : "Lock"}
        </button>
        <button
          onClick={() => setPopover(null)}
          className="text-xs rounded px-2 py-1 border border-border text-ink-muted hover:text-ink"
        >
          Close
        </button>
      </div>
    </div>
  );
}
{
  popover && (
    <div className="fixed inset-0 z-40" onClick={() => setPopover(null)} />
  );
}
```

**Step 5: Update AppCalendar.jsx to pass jsEvent to onEventClick**

In `handleEventClick`:

```javascript
const handleEventClick = (info) => {
  if (onEventClick) {
    onEventClick(info.event.extendedProps, info.jsEvent);
  }
};
```

**Step 6: Verify build**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: clean build

**Step 7: Commit**

```bash
git add frontend/src/pages/Schedule.jsx frontend/src/components/AppCalendar.jsx
git commit -m "feat: drag/resize auto-lock and popover unlock for study blocks"
```

---

## Final Verification

**Step 1: Full backend test suite**

```bash
docker compose exec -T backend python -m pytest tests/ -v --ignore=tests/test_syllabus_parser.py
```

Expected: All pass.

**Step 2: Frontend build**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: No errors.

**Step 3: Manual smoke test checklist**

- [ ] Import an ICS feed with timed events
- [ ] Click "Generate Study Times" — no overlap with imported events
- [ ] Import a Canvas deadline_marker event matching an assignment name
- [ ] Click "Generate Study Times" — study blocks end before the imported deadline
- [ ] Drag a study block — it turns darker green (locked), persists after re-generate
- [ ] Click a locked study block — popover shows "Unlock" button
- [ ] Click "Unlock" — block turns lighter green; next generate re-schedules it
- [ ] Drag into a busy imported event time — toast error, block snaps back

---

## Notes

- All backend test commands use Docker: `docker compose exec -T backend python -m pytest ...`
- After any Python file change: `docker compose up -d --build backend`
- PATCH endpoint uses raw `mysql.connector` (matching existing schedule.py pattern)
- `synchronize_session="fetch"` required on filtered `.delete()` when objects may be in ORM session
- Deadline reconciliation is **in-memory only** — does not write to Assignments table
- Only `event_kind='timed'` CalendarEvents are used as busy intervals; `deadline_marker` and `all_day` are excluded from busy constraints (they serve different roles)
