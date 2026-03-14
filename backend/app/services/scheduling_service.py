# Heuristics + engine.
# Input: term_id, DB session. Loads term with courses, assignments, and meetings,
# allocates study time blocks (15-min multiples, 8am–10pm, no conflicts).
# Uses a single min-cost max-flow pass to produce a balanced schedule.
# Meetings are recurring (day_of_week + start_time_str/end_time_str) or legacy one-off (start_time/end_time).
#
# DISCLAIMER: Project structure may change. Functions may be added or modified.

import heapq
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


class _MinCostMaxFlow:
    """
    Min-cost max-flow via successive shortest path with node potentials.
    Edges stored as [to, rev_index, residual_cap, cost] (mutable) for capacity updates.
    """

    def __init__(self, n: int) -> None:
        self.n = n
        self.g: list[list[list]] = [[] for _ in range(n)]
        # g[u] = [[v, rev, cap, cost], ...]; cap is residual capacity

    def add_edge(self, u: int, v: int, cap: int, cost: int) -> None:
        """Add directed edge u -> v with capacity and cost (cost can be zero)."""
        rev_u = len(self.g[u])
        rev_v = len(self.g[v])
        self.g[u].append([v, rev_v, cap, cost])
        self.g[v].append([u, rev_u, 0, -cost])

    def run(
        self, source: int, sink: int, flow_limit: int | None = None
    ) -> tuple[int, int]:
        """
        Push up to flow_limit units from source to sink at minimum cost.
        If flow_limit is None, push maximum flow.
        Returns (total_flow, total_cost).
        """
        flow_limit = flow_limit if flow_limit is not None else 10**18
        total_flow = 0
        total_cost = 0
        # Initial feasible potentials via Bellman-Ford (handles negative cost edges).
        pi = [10**18] * self.n
        pi[source] = 0
        for _ in range(self.n - 1):
            updated = False
            for u in range(self.n):
                if pi[u] == 10**18:
                    continue
                for e in self.g[u]:
                    v, _rev, cap, cost = e[0], e[1], e[2], e[3]
                    if cap > 0 and pi[v] > pi[u] + cost:
                        pi[v] = pi[u] + cost
                        updated = True
            if not updated:
                break
        for v in range(self.n):
            if pi[v] == 10**18:
                pi[v] = 0  # unreachable: keep 0 to avoid huge values

        while flow_limit > 0:
            # Shortest path in residual with reduced cost c + pi[u] - pi[v] (>= 0).
            dist = [10**18] * self.n
            dist[source] = 0
            prev: list[tuple[int, int] | None] = [None] * self.n
            heap: list[tuple[int, int]] = [(0, source)]
            while heap:
                d, u = heapq.heappop(heap)
                if d != dist[u]:
                    continue
                if u == sink:
                    break
                for idx, e in enumerate(self.g[u]):
                    v, rev, cap, cost = e[0], e[1], e[2], e[3]
                    if cap <= 0:
                        continue
                    c = cost + pi[u] - pi[v]
                    if c < 0:
                        c = 0
                    if dist[v] > d + c:
                        dist[v] = d + c
                        prev[v] = (u, idx)
                        heapq.heappush(heap, (dist[v], v))

            if dist[sink] == 10**18:
                break
            path_flow = flow_limit
            cur = sink
            while prev[cur] is not None:
                u, idx = prev[cur]
                path_flow = min(path_flow, self.g[u][idx][2])
                cur = u
            if path_flow <= 0:
                break
            cur = sink
            while prev[cur] is not None:
                u, idx = prev[cur]
                e = self.g[u][idx]
                v, rev, cap, cost = e[0], e[1], e[2], e[3]
                e[2] -= path_flow
                rev_e = self.g[v][rev]
                rev_e[2] += path_flow
                total_cost += path_flow * cost
                cur = u
            total_flow += path_flow
            flow_limit -= path_flow
            # Update potentials so reduced costs stay non-negative next iteration.
            for v in range(self.n):
                if dist[v] < 10**18:
                    pi[v] += dist[v]

        return (total_flow, total_cost)

    def get_flow(self, u: int, v: int) -> int:
        """Return flow sent on edge u -> v. Flow equals residual cap of backward edge v->u."""
        for e in self.g[u]:
            if e[0] == v:
                rev = e[1]
                return self.g[v][rev][2]  # backward edge's residual = flow on u->v
        return 0


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


def _generate_study_times_min_cost(
    session: Session,
    term: Term,
    assignments: list,
    meeting_busy: list[tuple[datetime, datetime]],
    tz: ZoneInfo,
    start_time: time,
    end_time: time,
    term_id: int,
    effective_due_dates: dict[int, datetime] | None,
    max_hours_per_day: int,
    allowed_weekdays: set[int] | None,
    dry_run: bool = False,
) -> list[StudyTime]:
    """
    Single-pass scheduling via min-cost max-flow. Builds a flow network where
    assignment->slot->day_tier->sink; day-tier edges have cost k^2 (k = tier index)
    so the solver spreads load across days (balanced schedule). Respects
    max_hours_per_day by capping tier count per day.
    Per-course study_hours_per_week is not enforced in this flow; callers may
    filter slots or post-process if needed.
    """
    # Normalize assignments and total demand
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
        total_required_slots += a.work_load

    if not normalized_assignments or total_required_slots == 0:
        return []

    # Build all 15-min slots across the term
    current_day = term.start_date if isinstance(term.start_date, date) else term.start_date.date()
    end_day = term.end_date if isinstance(term.end_date, date) else term.end_date.date()
    all_slots: list[tuple[datetime, datetime, int]] = []
    days: list[date] = []
    while current_day <= end_day:
        if allowed_weekdays is not None and current_day.weekday() not in allowed_weekdays:
            current_day = current_day + timedelta(days=1)
            continue
        day_idx = len(days)
        days.append(current_day)
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
        return []

    slots_per_day: list[int] = [0] * len(days)
    for _, _, di in all_slots:
        slots_per_day[di] += 1

    max_slots_per_day_cap = max_hours_per_day * 4
    if sum(slots_per_day) < total_required_slots:
        return []

    # Assignment -> slot indices (slots in assignment window)
    assignment_slot_indices: list[list[int]] = []
    for a, ws, we in normalized_assignments:
        indices = [
            idx
            for idx, (s, e, _) in enumerate(all_slots)
            if s >= ws and e <= we
        ]
        assignment_slot_indices.append(indices)

    for idx, (a, _, _) in enumerate(normalized_assignments):
        if a.work_load > 0 and not assignment_slot_indices[idx]:
            return []

    # Tie-breaker: prefer slots closest to due date (latest first). For each assignment,
    # rank its slots by (due - slot_start) ascending; rank 0 = closest to due.
    # We scale tier costs so this rank only breaks ties when tier cost would be equal.
    assignment_slot_cost: list[dict[int, int]] = []  # assignment index -> slot_idx -> cost (rank)
    cost_scale = len(all_slots) + 1  # tier costs multiplied by this so rank < scale
    for i, (a, _ws, we) in enumerate(normalized_assignments):
        # Sort slot indices by distance to due: (we - start) ascending => closest to due first
        sorted_slot_indices = sorted(
            assignment_slot_indices[i],
            key=lambda idx: (we - all_slots[idx][0]).total_seconds(),
        )
        assignment_slot_cost.append({idx: rank for rank, idx in enumerate(sorted_slot_indices)})

    # Day-tier nodes: for each day d, tiers 0..min(slots_per_day[d], cap)-1
    # Cost k^2 * cost_scale on slot->tier encourages spreading; assignment_slot cost breaks ties.
    num_tiers_per_day = [
        min(slots_per_day[d], max_slots_per_day_cap) for d in range(len(days))
    ]
    cumulative_tiers = [0] * (len(days) + 1)
    for d in range(len(days)):
        cumulative_tiers[d + 1] = cumulative_tiers[d] + num_tiers_per_day[d]
    total_tiers = cumulative_tiers[len(days)]

    num_assignments = len(normalized_assignments)
    num_slots = len(all_slots)
    # Nodes: 0=source, 1..num_assignments=assign, assign_offset+1..+num_slots=slots,
    #        tier_offset..tier_offset+total_tiers-1=tiers, sink
    assign_offset = 1
    slot_offset = assign_offset + num_assignments
    tier_offset = slot_offset + num_slots
    sink = tier_offset + total_tiers
    n_nodes = sink + 1

    mcmf = _MinCostMaxFlow(n_nodes)

    # Source -> assignments
    for i, (a, _, _) in enumerate(normalized_assignments):
        if a.work_load <= 0:
            continue
        mcmf.add_edge(0, assign_offset + i, a.work_load, 0)

    # Assignment -> slots (cap 1 each); cost = rank so "closest to due" is cheaper (tie-breaker)
    for i in range(num_assignments):
        cost_by_slot = assignment_slot_cost[i]
        for slot_idx in assignment_slot_indices[i]:
            rank_cost = cost_by_slot[slot_idx]
            mcmf.add_edge(assign_offset + i, slot_offset + slot_idx, 1, rank_cost)

    # Slot -> day-tier (each slot in day d connects to tiers of day d; cost k^2 * cost_scale)
    for slot_idx in range(num_slots):
        _, _, day_idx = all_slots[slot_idx]
        tier_start = cumulative_tiers[day_idx]
        tier_count = num_tiers_per_day[day_idx]
        for k in range(tier_count):
            tier_node = tier_offset + tier_start + k
            mcmf.add_edge(slot_offset + slot_idx, tier_node, 1, (k * k) * cost_scale)

    # Day-tier -> sink (cap 1 each)
    for tier_node in range(tier_offset, tier_offset + total_tiers):
        mcmf.add_edge(tier_node, sink, 1, 0)

    flow, _cost = mcmf.run(0, sink, flow_limit=total_required_slots)
    if flow < total_required_slots:
        return []

    # Extract assignment -> slot usage from flow
    used_slots_by_assignment: dict[int, list[int]] = {}
    for i, (a, _, _) in enumerate(normalized_assignments):
        used_slots_by_assignment[a.id] = []
        for slot_idx in assignment_slot_indices[i]:
            if mcmf.get_flow(assign_offset + i, slot_offset + slot_idx) == 1:
                used_slots_by_assignment[a.id].append(slot_idx)

    created: list[StudyTime] = []
    for a, _ws, _we in normalized_assignments:
        slot_indices = used_slots_by_assignment.get(a.id, [])
        intervals = [all_slots[idx][:2] for idx in slot_indices]
        merged = _merge_intervals(intervals)
        for start, end in merged:
            st = StudyTime(
                start_time=start,
                end_time=end,
                term_id=term_id,
                notes=None,
                assignment_id=a.id,
                course_id=a.course_id,
            )
            if not dry_run:
                session.add(st)
            created.append(st)

    return created


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
    study_time entries using a single min-cost max-flow pass:
    - Each assignment gets work_load * 15 minutes between its start_date and due_date.
    - Slots are 15 minutes, between study_start and study_end (default 8:00 - 22:00).
    - No conflict with course meetings or other study times.
    - Respects max_hours_per_day (from UserPreferences or param).
    - Balanced schedule: flow costs encourage spreading load across days (min-cost
      favors using "cheap" tier slots first, so no single day is overloaded).
    - Per-course study_hours_per_week is not enforced in this flow; see
      _generate_study_times_min_cost for details.

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

    # Schedule only assignments. study_hours_per_week is a per-course weekly cap (max hours
    # the student is willing to study for that course in a week), enforced when allocating.
    assignments = [a for course in term.courses for a in course.assignments]
    term_start = term.start_date if isinstance(term.start_date, date) else term.start_date.date()
    term_end = term.end_date if isinstance(term.end_date, date) else term.end_date.date()

    # Per-course weekly cap in minutes (None = no cap).
    max_minutes_per_week_by_course: dict[int, int] = {}
    for course in term.courses:
        hrs = course.study_hours_per_week
        if hrs is not None and hrs > 0:
            max_minutes_per_week_by_course[course.id] = min(168, int(hrs)) * 60
        # else: no cap for this course

    work_items = assignments
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

    # Single pass: min-cost max-flow for a balanced schedule (replaces slack-based + flow fallback).
    return _generate_study_times_min_cost(
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


