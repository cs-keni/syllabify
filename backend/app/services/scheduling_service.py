# Heuristics + engine.
# Input: term_id, DB session. Loads term with courses, assignments, and meetings,
# allocates study time blocks (15-min multiples, 8am–10pm, no conflicts).
# Goal: minimize max study minutes in a single day.
#
# DISCLAIMER: Project structure may change. Functions may be added or modified.

from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, joinedload

from app.models.term import Term
from app.models.study_time import StudyTime


# Default study window (can be overridden by user preferences later).
DEFAULT_STUDY_START = time(8, 0)   # 8:00 AM
DEFAULT_STUDY_END = time(22, 0)    # 10:00 PM
MINUTES_PER_SLOT = 15
MINUTES_PER_WORKLOAD_UNIT = 15


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


def generate_study_times(
    session: Session,
    term_id: int,
    study_start: time | None = None,
    study_end: time | None = None,
) -> list[StudyTime]:
    """
    Load the term by id, clear existing study times for it, then create new
    study_time entries so that:
    - Each assignment gets work_load * 15 minutes between its start_date and due_date.
    - Slots are 15 minutes, between study_start and study_end (default 8:00 - 22:00).
    - No conflict with course meetings or other study times.
    - Tries to minimize the maximum study minutes on any single day.

    Returns the list of created StudyTime instances (already added to session;
    caller should commit).
    """
    start_time = study_start if study_start is not None else DEFAULT_STUDY_START
    end_time = study_end if study_end is not None else DEFAULT_STUDY_END
    # Use module-level defaults for the rest of the function for consistency
    del study_start, study_end

    term = (
        session.query(Term)
        .options(
            joinedload(Term.courses).joinedload("assignments"),
            joinedload(Term.courses).joinedload("meetings"),
            joinedload(Term.study_times),
        )
        .filter(Term.id == term_id)
        .first()
    )
    if not term:
        raise ValueError(f"Term with id {term_id} not found.")

    # Collect all assignments across the term's courses
    assignments = [a for course in term.courses for a in course.assignments]
    if not assignments:
        return []

    # Timezone from first assignment
    tz = _get_tz(assignments[0].start_date)

    # Busy intervals: all meetings for this term's courses
    meeting_busy: list[tuple[datetime, datetime]] = []
    for course in term.courses:
        for meeting in course.meetings:
            meeting_busy.append((meeting.start_time, meeting.end_time))

    meeting_busy = _merge_intervals(meeting_busy)

    # Clear existing study times for this term
    session.query(StudyTime).filter(StudyTime.term_id == term_id).delete()

    # We'll add study times as we allocate, so they become busy for later assignments
    created: list[StudyTime] = []
    daily_minutes: dict[date, int] = {}  # date -> total study minutes so far

    # ----- Phase 1: Slack-based greedy scheduling -----

    # Precompute slack (available_minutes - required_minutes) for each assignment,
    # using only meetings as busy intervals.
    slack_by_assignment_id: dict[int, int] = {}
    for assignment in assignments:
        total_minutes = assignment.work_load * MINUTES_PER_WORKLOAD_UNIT
        if total_minutes <= 0:
            slack_by_assignment_id[assignment.id] = 0
            continue

        window_start = assignment.start_date
        window_end = assignment.due_date
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=tz)
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=tz)

        slots: list[tuple[datetime, datetime]] = []
        current = window_start
        one_day = timedelta(days=1)
        while current < window_end:
            day_end_dt = min(current + one_day, window_end)
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
    ordered_assignments = sorted(
        assignments,
        key=lambda a: (slack_by_assignment_id.get(a.id, 0), a.due_date),
    )

    # Start with meetings as busy; new study times will be added on top.
    busy: list[tuple[datetime, datetime]] = list(meeting_busy)

    all_fully_allocated = True

    for assignment in ordered_assignments:
        total_minutes = assignment.work_load * MINUTES_PER_WORKLOAD_UNIT
        if total_minutes <= 0:
            continue

        window_start = assignment.start_date
        window_end = assignment.due_date
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

        # Sort by (daily total so far, start time) to prefer low-load days first.
        def slot_key(s: tuple[datetime, datetime]) -> tuple[int, datetime]:
            d = s[0].date()
            return (daily_minutes.get(d, 0), s[0])

        slots.sort(key=slot_key)

        needed_slots = total_minutes // MINUTES_PER_SLOT
        used = 0
        new_busy: list[tuple[datetime, datetime]] = []
        for start, end in slots:
            if used >= needed_slots:
                break
            st = StudyTime(
                start_time=start,
                end_time=end,
                term_id=term_id,
                notes=None,
            )
            session.add(st)
            created.append(st)
            new_busy.append((start, end))
            d = start.date()
            daily_minutes[d] = daily_minutes.get(d, 0) + MINUTES_PER_SLOT
            used += 1

        busy.extend(new_busy)
        busy = _merge_intervals(busy)

        if used < needed_slots:
            all_fully_allocated = False

    if all_fully_allocated:
        return created

    # ----- Phase 2: Global solver fallback (minimize max daily study time) -----

    # Remove any partially-created study times from the greedy phase.
    session.query(StudyTime).filter(StudyTime.term_id == term_id).delete()

    # Use a global optimization approach as a fallback. This will:
    # - Use all 15-minute slots across the term (respecting meetings and study window),
    # - Minimize the maximum study minutes on any day,
    # - Fully allocate all assignments if it is mathematically possible.
    global_created = _generate_study_times_global(
        session=session,
        term=term,
        assignments=assignments,
        meeting_busy=meeting_busy,
        tz=tz,
        start_time=start_time,
        end_time=end_time,
        term_id=term_id,
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
        INF = 10**18
        while self._bfs(s, t):
            self.it = [0] * self.n
            f = self._dfs(s, t, INF)
            while f > 0:
                flow += f
                f = self._dfs(s, t, INF)
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
        we = a.due_date
        if ws.tzinfo is None:
            ws = ws.replace(tzinfo=tz)
        if we.tzinfo is None:
            we = we.replace(tzinfo=tz)
        normalized_assignments.append((a, ws, we))
        total_required_slots += a.work_load  # each workload unit == one 15-min slot

    if not normalized_assignments or total_required_slots == 0:
        return []

    # Build all possible 15-min slots across the term, excluding meetings.
    # Slots are constrained to the study window [start_time, end_time].
    from math import inf

    earliest = min(ws for _, ws, _ in normalized_assignments)
    latest = max(we for _, _, we in normalized_assignments)

    all_slots: list[tuple[datetime, datetime, int]] = []
    days: list[date] = []
    day_index_by_date: dict[date, int] = {}

    current_day = earliest.date()
    end_day = latest.date()
    while current_day <= end_day:
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
    max_slots_in_any_day = max(slots_per_day) if slots_per_day else 0
    low = 0
    high = max_slots_in_any_day
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

    # If even allowing all slots per day we cannot satisfy demand, return empty.
    if build_and_run_flow(max_slots_in_any_day) < total_required_slots:
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

    created: list[StudyTime] = []
    for a, _ws, _we in normalized_assignments:
        slot_indices = used_slots_by_assignment.get(a.id, [])
        for idx in slot_indices:
            s, e, _di = all_slots[idx]
            st = StudyTime(
                start_time=s,
                end_time=e,
                term_id=term_id,
                notes=None,
            )
            session.add(st)
            created.append(st)

    return created
