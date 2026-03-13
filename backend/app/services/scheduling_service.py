# Heuristics + engine.
# Input: term_id, DB session. Loads term with courses, assignments, and meetings,
# allocates study time blocks (15-min multiples, 8am–10pm, no conflicts).
# Goal: minimize max study minutes in a single day.
# Meetings are recurring (day_of_week + start_time_str/end_time_str) or legacy one-off (start_time/end_time).
#
# DISCLAIMER: Project structure may change. Functions may be added or modified.

import re as _re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, joinedload

# Import all models referenced by Term's relationships so SQLAlchemy can resolve
# them when configuring the mapper (avoids InvalidRequestError: failed to locate 'User').
from app.models.assignment import Assignment  # noqa: F401
from app.models.calendar_event import CalendarEvent
from app.models.calendar_source import (
    CalendarSource,  # noqa: F401 - needed for CalendarEvent.source relationship
)
from app.models.course import Course  # noqa: F401
from app.models.meeting import Meeting  # noqa: F401
from app.models.study_time import StudyTime
from app.models.term import Term
from app.models.user import User  # noqa: F401

# Default study window (can be overridden by user preferences later).
DEFAULT_STUDY_START = time(8, 0)   # 8:00 AM
DEFAULT_STUDY_END = time(22, 0)    # 10:00 PM
MINUTES_PER_SLOT = 15
MINUTES_PER_WORKLOAD_UNIT = 15

# Synthetic id base for ongoing (non-assignment) study work; avoids collision with real assignment ids.
_ONGOING_ID_BASE = -1000000

# Recurring meeting: 2-char day codes (MO, TU, ...) -> Python weekday (Mon=0, ..., Sun=6).
_DAY_CODE_TO_WEEKDAY = {
    "MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6,
}


def _parse_preferred_days(csv: str | None) -> set[int] | None:
    """Parse 'MO,TU,WE,TH,FR' into set of weekdays. None = allow all days."""
    if not csv or not isinstance(csv, str):
        return None
    codes = [c.strip().upper()[:2] for c in csv.split(",") if c.strip()]
    if not codes:
        return None
    weekdays = set()
    for c in codes:
        w = _DAY_CODE_TO_WEEKDAY.get(c)
        if w is not None:
            weekdays.add(w)
    return weekdays if weekdays else None


def _parse_time_str(s: str | None) -> time | None:
    """Parse 'HH:MM' or 'H:MM' string to time. Returns None if invalid or empty."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        parts = s.split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0], 10), int(parts[1], 10)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return time(h, m)
    except (ValueError, TypeError):
        pass
    return None


def _meetings_to_busy_intervals(
    term: Term,
    courses: list,
    tz: ZoneInfo,
) -> list[tuple[datetime, datetime]]:
    """
    Expand all meetings for the term's courses into (start, end) datetime intervals.
    - Recurring: day_of_week + start_time_str + end_time_str over term.start_date..term.end_date.
    - Legacy one-off: meeting.start_time / meeting.end_time if set.
    """
    intervals: list[tuple[datetime, datetime]] = []
    term_start = term.start_date
    term_end = term.end_date
    if term_start is None or term_end is None:
        return intervals
    current = term_start
    one_day = timedelta(days=1)
    while current <= term_end:
        for course in courses:
            for meeting in course.meetings:
                # Recurring: day_of_week + start_time_str, end_time_str
                if meeting.day_of_week and meeting.start_time_str and meeting.end_time_str:
                    day_code = (meeting.day_of_week or "").strip().upper()
                    weekday = _DAY_CODE_TO_WEEKDAY.get(day_code)
                    if weekday is None or current.weekday() != weekday:
                        continue
                    start_t = _parse_time_str(meeting.start_time_str)
                    end_t = _parse_time_str(meeting.end_time_str)
                    if start_t is None or end_t is None:
                        continue
                    start_dt = datetime.combine(current, start_t, tzinfo=tz)
                    end_dt = datetime.combine(current, end_t, tzinfo=tz)
                    if end_dt <= start_dt:
                        continue
                    intervals.append((start_dt, end_dt))
                # Legacy one-off: start_time, end_time
                elif meeting.start_time is not None and meeting.end_time is not None:
                    s, e = meeting.start_time, meeting.end_time
                    if s.tzinfo is None:
                        s = s.replace(tzinfo=tz)
                    if e.tzinfo is None:
                        e = e.replace(tzinfo=tz)
                    if e > s:
                        intervals.append((s, e))
        current += one_day
    return intervals


def _normalize_title(raw: str) -> str:
    """Normalize titles for fuzzy deadline matching."""
    s = (raw or "").lower().strip()
    for prefix in ("due:", "assignment:", "hw:", "homework:", "project:", "quiz:", "exam:"):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    return _re.sub(r"[^\w\s]", "", s).strip()


def _ensure_utc(dt: datetime) -> datetime:
    """Return an aware UTC datetime; naive datetimes are assumed UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("UTC"))


def _get_tz(dt: datetime) -> ZoneInfo:
    """Infer timezone from a datetime; default to UTC if naive or unknown."""
    if dt.tzinfo is None:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(dt.tzinfo.key) if hasattr(dt.tzinfo, "key") else ZoneInfo("UTC")
    except Exception:
        return ZoneInfo("UTC")


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Merge overlapping (start, end) intervals. Input must be sortable by start."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _free_slots_for_day(
    day_start: datetime,
    day_end: datetime,
    busy: list[tuple[datetime, datetime]],
    slot_minutes: int,
    tz: ZoneInfo,
    study_start_time: time,
    study_end_time: time,
) -> list[tuple[datetime, datetime]]:
    """
    Given a day range [day_start, day_end] and busy intervals (e.g. meetings),
    return a list of (start, end) free slots, each of length slot_minutes.
    """
    study_start = datetime.combine(day_start.date(), study_start_time, tzinfo=tz)
    study_end = datetime.combine(day_end.date(), study_end_time, tzinfo=tz)
    # Clamp to actual day range
    window_start = max(day_start, study_start)
    window_end = min(day_end, study_end)
    if window_start >= window_end:
        return []

    # Clip busy to this day and merge
    day_busy = []
    for s, e in busy:
        if e <= window_start or s >= window_end:
            continue
        day_busy.append((max(s, window_start), min(e, window_end)))
    day_busy = _merge_intervals(day_busy)

    # Build free gaps
    free = []
    current = window_start
    for s, e in day_busy:
        if current < s:
            free.append((current, s))
        current = max(current, e)
    if current < window_end:
        free.append((current, window_end))

    # Chunk free gaps into slot_minutes-long slots
    slot_delta = timedelta(minutes=slot_minutes)
    slots = []
    for start, end in free:
        while start + slot_delta <= end:
            slots.append((start, start + slot_delta))
            start += slot_delta
    return slots


def _reconcile_deadlines(session: Session, user_id: int, assignments: list) -> dict[int, datetime]:
    """
    Return assignment.id -> effective due datetime using imported deadline markers.
    Imported dates only override when they are earlier than assignment.due_date.
    """
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
    window_seconds = 14 * 24 * 60 * 60

    for assignment in assignments:
        due = _ensure_utc(assignment.due_date)
        effective[assignment.id] = due

        normalized_assignment = _normalize_title(assignment.assignment_name or "")
        best_match_due: datetime | None = None
        best_delta: float | None = None

        for marker in markers:
            if marker.start_date:
                marker_due = datetime.combine(
                    marker.start_date, time(23, 59, 59), tzinfo=ZoneInfo("UTC")
                )
            elif marker.start_time:
                marker_due = _ensure_utc(marker.start_time)
            else:
                continue

            if abs((marker_due - due).total_seconds()) > window_seconds:
                continue

            normalized_marker = _normalize_title(marker.title or "")
            if not normalized_assignment or not normalized_marker:
                continue
            if (
                normalized_assignment not in normalized_marker
                and normalized_marker not in normalized_assignment
            ):
                continue

            delta = abs((marker_due - due).total_seconds())
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_match_due = marker_due

        if best_match_due is not None and best_match_due < due:
            effective[assignment.id] = best_match_due

    return effective


def generate_study_times(
    session: Session,
    term_id: int,
    study_start: time | None = None,
    study_end: time | None = None,
    max_hours_per_day: int | None = None,
    user_timezone: str | None = None,
    preferred_days: str | None = None,
    dry_run: bool = False,
) -> list[StudyTime]:
    """
    Load the term by id, clear existing study times for it, then create new
    study_time entries so that:
    - Each assignment gets work_load * 15 minutes between its start_date and due_date.
    - Slots are 15 minutes, between study_start and study_end (default 8:00 - 22:00).
    - No conflict with course meetings or other study times.
    - Respects max_hours_per_day (from UserPreferences or param).
    - Tries to minimize the maximum study minutes on any single day.

    Returns the list of created StudyTime instances (already added to session;
    caller should commit).
    """
    start_time = study_start if study_start is not None else DEFAULT_STUDY_START
    end_time = study_end if study_end is not None else DEFAULT_STUDY_END
    if max_hours_per_day is not None:
        max_hours = max(1, min(24, max_hours_per_day))
    else:
        max_hours = 8  # fallback when called without prefs (e.g. tests)
    del study_start, study_end, max_hours_per_day

    term = (
        session.query(Term)
        .options(
            joinedload(Term.courses).joinedload(Course.assignments),
            joinedload(Term.courses).joinedload(Course.meetings),
            joinedload(Term.study_times),
        )
        .filter(Term.id == term_id)
        .first()
    )
    if not term:
        raise ValueError(f"Term with id {term_id} not found.")

    # Collect assignments and add ongoing study (study_hours_per_week spread across term).
    # Ongoing ensures study blocks throughout the term, not just before assignment due dates.
    assignments = [a for course in term.courses for a in course.assignments]
    term_start = term.start_date if isinstance(term.start_date, date) else term.start_date.date()
    term_end = term.end_date if isinstance(term.end_date, date) else term.end_date.date()
    num_weeks = max(1, (term_end - term_start).days / 7.0)

    class _OngoingWork:
        """Synthetic work item for ongoing course study (assignment_id=None in StudyTime)."""

        def __init__(self, course_id: int, work_load: int, start_d: date, due_d: date):
            self.id = _ONGOING_ID_BASE - course_id
            self.course_id = course_id
            self.work_load = work_load
            self.start_date = datetime.combine(start_d, time(0, 0), tzinfo=ZoneInfo("UTC"))
            self.due_date = datetime.combine(due_d, time(23, 59), tzinfo=ZoneInfo("UTC"))

    ongoing: list = []
    for course in term.courses:
        hrs_per_week = course.study_hours_per_week if course.study_hours_per_week is not None else 5
        hrs_per_week = max(1, min(168, int(hrs_per_week)))  # clamp 1-168
        work_load = max(1, int(hrs_per_week * num_weeks * 4))  # 4 slots per hour
        ongoing.append(_OngoingWork(course.id, work_load, term_start, term_end))

    work_items = assignments + ongoing
    if not work_items:
        return []

    # Use user's timezone so 5pm-10pm is correct (not UTC)
    if user_timezone:
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = _get_tz(work_items[0].start_date)
    else:
        tz = _get_tz(work_items[0].start_date)

    allowed_weekdays = _parse_preferred_days(preferred_days)

    # Busy intervals: expand recurring and one-off meetings into (start, end) intervals
    meeting_busy = _meetings_to_busy_intervals(term, term.courses, tz)
    meeting_busy = _merge_intervals(meeting_busy)

    # Active timed calendar events block scheduling.
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
            s = _ensure_utc(s)
            e = _ensure_utc(e)
            calendar_busy.append((s, e))

    # All-day events block the study window for each day in their range.
    all_day_events = (
        session.query(CalendarEvent)
        .filter(
            CalendarEvent.user_id == user_id,
            CalendarEvent.event_kind == "all_day",
            CalendarEvent.sync_status == "active",
            CalendarEvent.start_date.isnot(None),
        )
        .all()
    )
    for evt in all_day_events:
        ev_start = evt.start_date
        ev_end = evt.end_date if evt.end_date else evt.start_date
        ev_end = max(ev_start, ev_end)
        day_range = (max(term_start, ev_start), min(term_end, ev_end))
        if day_range[0] > day_range[1]:
            continue
        d = day_range[0]
        while d <= day_range[1]:
            slot_start = datetime.combine(d, start_time, tzinfo=tz)
            slot_end = datetime.combine(d, end_time, tzinfo=tz)
            calendar_busy.append((slot_start.astimezone(ZoneInfo("UTC")), slot_end.astimezone(ZoneInfo("UTC"))))
            d += timedelta(days=1)

    meeting_busy = _merge_intervals(meeting_busy + calendar_busy)
    effective_due_dates = _reconcile_deadlines(session, user_id, assignments)

    locked_study_times = (
        session.query(StudyTime)
        .filter(StudyTime.term_id == term_id, StudyTime.is_locked.is_(True))
        .all()
    )
    if not dry_run:
        session.query(StudyTime).filter(
            StudyTime.term_id == term_id, StudyTime.is_locked.is_(False)
        ).delete(synchronize_session="fetch")

    locked_busy: list[tuple[datetime, datetime]] = []
    for locked in locked_study_times:
        if locked.start_time and locked.end_time:
            locked_busy.append((_ensure_utc(locked.start_time), _ensure_utc(locked.end_time)))

    meeting_busy = _merge_intervals(meeting_busy + locked_busy)

    # We'll add study times as we allocate, so they become busy for later work items
    created: list[StudyTime] = []
    daily_minutes: dict[date, int] = {}  # date -> total study minutes so far
    weekly_minutes: dict[tuple[int, int], int] = {}  # (year, week) -> total minutes (for spreading)

    def _week_key(d: date) -> tuple[int, int]:
        return (d.isocalendar()[0], d.isocalendar()[1])

    # ----- Phase 1: Slack-based greedy scheduling -----

    # Precompute slack (available_minutes - required_minutes) for each work item,
    # using only meetings as busy intervals.
    slack_by_assignment_id: dict[int, int] = {}
    for assignment in work_items:
        total_minutes = assignment.work_load * MINUTES_PER_WORKLOAD_UNIT
        if total_minutes <= 0:
            slack_by_assignment_id[assignment.id] = 0
            continue

        window_start = assignment.start_date
        window_end = effective_due_dates.get(assignment.id, assignment.due_date)
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=tz)
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=tz)

        slots: list[tuple[datetime, datetime]] = []
        current = window_start
        one_day = timedelta(days=1)
        while current < window_end:
            day_end_dt = min(current + one_day, window_end)
            if allowed_weekdays is None or current.date().weekday() in allowed_weekdays:
                day_slots = _free_slots_for_day(
                    current,
                    day_end_dt,
                    meeting_busy,
                    MINUTES_PER_SLOT,
                    tz,
                    start_time,
                    end_time,
                )
                slots.extend(day_slots)
            current = day_end_dt

        available_minutes = len(slots) * MINUTES_PER_SLOT
        slack_by_assignment_id[assignment.id] = available_minutes - total_minutes

    # Use slack-based ordering (least slack first, then by due date).
    ordered_work_items = sorted(
        work_items,
        key=lambda a: (slack_by_assignment_id.get(a.id, 0), a.due_date),
    )

    # Start with meetings as busy; new study times will be added on top.
    busy: list[tuple[datetime, datetime]] = list(meeting_busy)

    all_fully_allocated = True

    for assignment in ordered_work_items:
        total_minutes = assignment.work_load * MINUTES_PER_WORKLOAD_UNIT
        if total_minutes <= 0:
            continue

        window_start = assignment.start_date
        window_end = effective_due_dates.get(assignment.id, assignment.due_date)
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=tz)
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=tz)

        # Collect all free 15-min slots in [window_start, window_end],
        # taking into account meetings + already allocated study times.
        slots: list[tuple[datetime, datetime]] = []
        current = window_start
        one_day = timedelta(days=1)
        while current < window_end:
            day_end_dt = min(current + one_day, window_end)
            if allowed_weekdays is None or current.date().weekday() in allowed_weekdays:
                day_slots = _free_slots_for_day(
                    current,
                    day_end_dt,
                    busy,
                    MINUTES_PER_SLOT,
                    tz,
                    start_time,
                    end_time,
                )
                slots.extend(day_slots)
            current = day_end_dt

        # Sort by (weekly total, daily total, start time) to spread across weeks and days.
        def slot_key(s: tuple[datetime, datetime]) -> tuple[int, int, datetime]:
            d = s[0].date()
            wk = _week_key(d)
            return (weekly_minutes.get(wk, 0), daily_minutes.get(d, 0), s[0])

        slots.sort(key=slot_key)

        needed_slots = total_minutes // MINUTES_PER_SLOT
        used = 0
        used_slots: list[tuple[datetime, datetime]] = []
        max_minutes_per_day = max_hours * 60
        for start, end in slots:
            if used >= needed_slots:
                break
            d = start.date()
            if daily_minutes.get(d, 0) + MINUTES_PER_SLOT > max_minutes_per_day:
                continue  # skip this slot to respect max_hours_per_day
            used_slots.append((start, end))
            daily_minutes[d] = daily_minutes.get(d, 0) + MINUTES_PER_SLOT
            weekly_minutes[_week_key(d)] = weekly_minutes.get(_week_key(d), 0) + MINUTES_PER_SLOT
            used += 1

        # Merge adjacent 15-min slots into contiguous blocks (e.g. 5:00-5:15, 5:15-5:30 -> 5:00-5:30).
        merged = _merge_intervals(used_slots)
        aid = assignment.id if assignment.id >= 0 else None  # ongoing work has negative id
        for start, end in merged:
            st = StudyTime(
                start_time=start,
                end_time=end,
                term_id=term_id,
                notes=None,
                assignment_id=aid,
                course_id=assignment.course_id,
            )
            if not dry_run:
                session.add(st)
            created.append(st)
        busy.extend(used_slots)
        busy = _merge_intervals(busy)

        if used < needed_slots:
            all_fully_allocated = False

    if all_fully_allocated:
        return created

    # ----- Phase 2: Global solver fallback (minimize max daily study time) -----

    # Remove any partially-created study times from the greedy phase.
    if not dry_run:
        session.query(StudyTime).filter(
            StudyTime.term_id == term_id, StudyTime.is_locked.is_(False)
        ).delete(synchronize_session="fetch")

    # Use a global optimization approach as a fallback. This will:
    # - Use all 15-minute slots across the term (respecting meetings and study window),
    # - Minimize the maximum study minutes on any day,
    # - Fully allocate all assignments if it is mathematically possible.
    global_created = _generate_study_times_global(
        session=session,
        term=term,
        assignments=work_items,
        meeting_busy=meeting_busy,
        tz=tz,
        start_time=start_time,
        end_time=end_time,
        term_id=term_id,
        effective_due_dates=effective_due_dates,
        max_hours_per_day=max_hours,
        allowed_weekdays=allowed_weekdays,
        dry_run=dry_run,
    )
    return global_created


class _FlowEdge:
    def __init__(self, to: int, rev: int, cap: int) -> None:
        self.to = to
        self.rev = rev
        self.cap = cap


class _Dinic:
    def __init__(self, n: int) -> None:
        self.n = n
        self.g: list[list[_FlowEdge]] = [[] for _ in range(n)]
        self.level: list[int] = [0] * n
        self.it: list[int] = [0] * n

    def add_edge(self, fr: int, to: int, cap: int) -> None:
        fwd = _FlowEdge(to, len(self.g[to]), cap)
        rev = _FlowEdge(fr, len(self.g[fr]), 0)
        self.g[fr].append(fwd)
        self.g[to].append(rev)

    def _bfs(self, s: int, t: int) -> bool:
        from collections import deque

        self.level = [-1] * self.n
        q = deque()
        self.level[s] = 0
        q.append(s)
        while q:
            v = q.popleft()
            for e in self.g[v]:
                if e.cap > 0 and self.level[e.to] < 0:
                    self.level[e.to] = self.level[v] + 1
                    q.append(e.to)
        return self.level[t] >= 0

    def _dfs(self, v: int, t: int, f: int) -> int:
        if v == t:
            return f
        for i in range(self.it[v], len(self.g[v])):
            self.it[v] = i
            e = self.g[v][i]
            if e.cap > 0 and self.level[v] < self.level[e.to]:
                d = self._dfs(e.to, t, min(f, e.cap))
                if d > 0:
                    e.cap -= d
                    self.g[e.to][e.rev].cap += d
                    return d
        return 0

    def max_flow(self, s: int, t: int) -> int:
        flow = 0
        inf_cap = 10**18
        while self._bfs(s, t):
            self.it = [0] * self.n
            f = self._dfs(s, t, inf_cap)
            while f > 0:
                flow += f
                f = self._dfs(s, t, inf_cap)
        return flow


def _generate_study_times_global(
    session: Session,
    term: Term,
    assignments: list,
    meeting_busy: list[tuple[datetime, datetime]],
    tz: ZoneInfo,
    start_time: time,
    end_time: time,
    term_id: int,
    effective_due_dates: dict[int, datetime] | None = None,
    max_hours_per_day: int | None = None,
    allowed_weekdays: set[int] | None = None,
    dry_run: bool = False,
) -> list[StudyTime]:
    """
    Global optimal scheduling using max-flow + binary search on the maximum
    allowed minutes per day. Guarantees:
    - If a conflict-free, fully allocated schedule exists within the term's
      study window and meetings, this will find one.
    - Among all such schedules, it minimizes the maximum study minutes on any day.
    """
    # Normalize assignment windows to the same timezone and compute total demand.
    normalized_assignments = []
    total_required_slots = 0
    for a in assignments:
        if a.work_load <= 0:
            continue
        ws = a.start_date
        we = (
            effective_due_dates.get(a.id, a.due_date)
            if effective_due_dates is not None
            else a.due_date
        )
        if ws.tzinfo is None:
            ws = ws.replace(tzinfo=tz)
        if we.tzinfo is None:
            we = we.replace(tzinfo=tz)
        normalized_assignments.append((a, ws, we))
        total_required_slots += a.work_load  # each workload unit == one 15-min slot

    if not normalized_assignments or total_required_slots == 0:
        return []

    # Build all possible 15-min slots across the full term (not just assignment windows).
    # This ensures work is spread across the course span even when assignments have gaps.
    # Slots are constrained to the study window [start_time, end_time].
    current_day = term.start_date if isinstance(term.start_date, date) else term.start_date.date()
    end_day = term.end_date if isinstance(term.end_date, date) else term.end_date.date()

    all_slots: list[tuple[datetime, datetime, int]] = []
    days: list[date] = []
    day_index_by_date: dict[date, int] = {}
    while current_day <= end_day:
        if allowed_weekdays is not None and current_day.weekday() not in allowed_weekdays:
            current_day = current_day + timedelta(days=1)
            continue
        day_idx = len(days)
        days.append(current_day)
        day_index_by_date[current_day] = day_idx

        # Build free slots for this day using only meetings as busy.
        day_start_dt = datetime.combine(current_day, start_time, tzinfo=tz)
        day_end_dt = datetime.combine(current_day, end_time, tzinfo=tz)
        day_slots = _free_slots_for_day(
            day_start_dt,
            day_end_dt,
            meeting_busy,
            MINUTES_PER_SLOT,
            tz,
            start_time,
            end_time,
        )
        for s, e in day_slots:
            all_slots.append((s, e, day_idx))

        current_day = current_day + timedelta(days=1)

    if not all_slots:
        # No free slots at all.
        return []

    slots_per_day: list[int] = [0] * len(days)
    for _, _, di in all_slots:
        slots_per_day[di] += 1

    # Quick infeasibility check: total capacity < total demand.
    if sum(slots_per_day) < total_required_slots:
        return []

    # For each assignment, compute which slot indices it can use.
    assignment_slot_indices: list[list[int]] = []
    for a, ws, we in normalized_assignments:
        indices: list[int] = []
        for idx, (s, e, _di) in enumerate(all_slots):
            if s >= ws and e <= we:
                indices.append(idx)
        assignment_slot_indices.append(indices)

    # If any assignment has no usable slots, global solution is impossible.
    for idx, (a, _, _) in enumerate(normalized_assignments):
        if a.work_load > 0 and not assignment_slot_indices[idx]:
            return []

    # Binary search on the maximum number of slots allowed per day.
    # Cap by user's max_hours_per_day so we never exceed their preferred daily limit.
    max_slots_in_any_day = max(slots_per_day) if slots_per_day else 0
    max_hrs = max_hours_per_day if max_hours_per_day is not None else 8
    max_slots_per_day_cap = max_hrs * 4  # 4 slots per hour (15-min slots)
    high = min(max_slots_in_any_day, max_slots_per_day_cap)
    low = 0
    best_limit = None
    best_flow_graph: _Dinic | None = None
    best_node_indices: dict[str, int] | None = None

    def build_and_run_flow(limit_per_day: int, keep_graph: bool = False):
        nonlocal best_flow_graph, best_node_indices

        num_assignments = len(normalized_assignments)
        num_slots = len(all_slots)
        num_days = len(days)

        # Node layout:
        # 0: source
        # [1 .. num_assignments]: assignment nodes
        # [1 + num_assignments .. num_assignments + num_slots]: slot nodes
        # [1 + num_assignments + num_slots .. num_assignments + num_slots + num_days]: day nodes
        # last index: sink
        source = 0
        assign_offset = 1
        slot_offset = assign_offset + num_assignments
        day_offset = slot_offset + num_slots
        sink = day_offset + num_days
        node_count = sink + 1

        dinic = _Dinic(node_count)

        # Source -> assignments (capacity = workload in slots).
        for i, (a, _ws, _we) in enumerate(normalized_assignments):
            if a.work_load <= 0:
                continue
            dinic.add_edge(source, assign_offset + i, a.work_load)

        # Assignment -> slots (each edge capacity 1).
        for i in range(len(normalized_assignments)):
            from_node = assign_offset + i
            for slot_idx in assignment_slot_indices[i]:
                dinic.add_edge(from_node, slot_offset + slot_idx, 1)

        # Slot -> day (each slot belongs to exactly one day, capacity 1).
        for slot_idx, (_s, _e, di) in enumerate(all_slots):
            dinic.add_edge(slot_offset + slot_idx, day_offset + di, 1)

        # Day -> sink (capacity = min(limit_per_day, available slots)).
        for di, count in enumerate(slots_per_day):
            cap = min(limit_per_day, count)
            if cap > 0:
                dinic.add_edge(day_offset + di, sink, cap)

        flow = dinic.max_flow(source, sink)

        if keep_graph and flow == total_required_slots:
            best_flow_graph = dinic
            best_node_indices = {
                "source": source,
                "assign_offset": assign_offset,
                "slot_offset": slot_offset,
                "day_offset": day_offset,
                "sink": sink,
            }

        return flow

    # If we cannot satisfy demand within the user's max_hours_per_day cap, return empty.
    if build_and_run_flow(high) < total_required_slots:
        return []

    while low <= high:
        mid = (low + high) // 2
        flow = build_and_run_flow(mid)
        if flow == total_required_slots:
            best_limit = mid
            high = mid - 1
        else:
            low = mid + 1

    if best_limit is None:
        return []

    # Re-run with the best limit and keep the graph to extract the assignment.
    build_and_run_flow(best_limit, keep_graph=True)
    assert best_flow_graph is not None and best_node_indices is not None

    dinic = best_flow_graph
    assign_offset = best_node_indices["assign_offset"]
    slot_offset = best_node_indices["slot_offset"]

    # Extract which slots were used by looking for saturated assignment->slot edges.
    used_slots_by_assignment: dict[int, list[int]] = {}
    for i, (a, _ws, _we) in enumerate(normalized_assignments):
        node = assign_offset + i
        for edge in dinic.g[node]:
            # Edge to a slot node?
            if slot_offset <= edge.to < slot_offset + len(all_slots):
                # Original capacity was 1; if cap == 0 now, this edge carried flow.
                if edge.cap == 0:
                    slot_idx = edge.to - slot_offset
                    used_slots_by_assignment.setdefault(a.id, []).append(slot_idx)

    # Merge adjacent 15-min slots into contiguous blocks per assignment.
    created: list[StudyTime] = []
    for a, _ws, _we in normalized_assignments:
        slot_indices = used_slots_by_assignment.get(a.id, [])
        intervals = [all_slots[idx][:2] for idx in slot_indices]  # (start, end) per slot
        merged = _merge_intervals(intervals)  # e.g. 5:00-5:15, 5:15-5:30 -> 5:00-5:30
        aid = a.id if a.id >= 0 else None  # ongoing work has negative id
        for start, end in merged:
            st = StudyTime(
                start_time=start,
                end_time=end,
                term_id=term_id,
                notes=None,
                assignment_id=aid,
                course_id=a.course_id,
            )
            if not dry_run:
                session.add(st)
            created.append(st)

    return created
