# Syllabify — TikTok Phone Screen Prep

> Role: Backend Software Engineer, Social Graph  
> Format: Answer these out loud, naturally — don't read verbatim. Use as a mental model.

---

## Core Understanding

### What problem does this project solve?

University students get syllabus PDFs with due dates, but no guidance on *when* to actually work. You might have three things due on Friday and only realize it Thursday night. Existing tools like Canvas or Notion track deadlines — they don't tell you when to sit down and study.

Syllabify automates that last mile. Upload your syllabus, and the system extracts all assignments, estimates how long each will take, and generates a personalized study schedule across your whole semester — respecting your class meetings, calendar events, work-hour preferences, and per-course time caps. The result lands directly in your calendar.

### What are the main components of the system?

Five main pieces:

1. **Parsing pipeline** — takes a PDF or pasted text, runs rule-based extraction first, falls back to an LLM (OpenAI) for ambiguous fields. Outputs course name, assignments, estimated hours, and meeting times.

2. **Scheduling engine** — a min-cost max-flow solver. Takes assignments (with work estimates and deadlines), available time slots (15-minute blocks across the term), and constraints (busy calendar events, user preferences), and outputs an optimal study schedule.

3. **REST API** — Flask, ~10 blueprints. Handles auth (JWT + Google OAuth), course/assignment CRUD, schedule generation, calendar sync, and iCal export.

4. **Relational database** — MySQL/PostgreSQL (3NF). Users → Terms → Courses → Assignments, with StudyTimes as the output of the scheduler. Cascading deletes for clean teardown.

5. **Frontend** — React + Tailwind. FullCalendar grid for viewing the schedule, multi-step upload/review flow, and a dashboard with upcoming deadlines.

### How does data flow through the system?

**Upload flow:**
1. User uploads PDF → `POST /api/syllabus/parse`
2. Backend runs hybrid extraction: regex + structure heuristics first, OpenAI fallback for uncertain fields
3. Returns parsed data with a confidence score; user reviews and edits in the UI
4. User confirms → course + assignments + meetings written to DB
5. Schedule auto-generates (in preview mode first — dry run, nothing committed)
6. User approves → study times committed to DB

**Schedule generation flow:**
1. Load term with all courses, assignments, meetings
2. Pull user's calendar events (Google Calendar / iCal feeds) to mark as busy
3. Enumerate every 15-minute slot across the term; filter by work hours, preferred days
4. Build a flow network (more on this below)
5. Run MCMF → extract used slots per assignment
6. Post-flow: enforce per-course weekly hour caps by dropping lowest-priority blocks
7. Merge adjacent blocks → write StudyTime records

**Export flow:**
Study times → iCal feed (token-authenticated public endpoint) → subscribe in any calendar app

### What are the key algorithms used?

The core is **min-cost max-flow (MCMF)** with successive shortest paths and Dijkstra + node potentials.

The flow network:
- **Source → Assignment nodes:** capacity = work_load in 15-min units, cost 0
- **Assignment → Slot nodes:** capacity 1, cost = rank of slot relative to assignment's deadline (encourages scheduling closer to due date)
- **Slot → SlotCap nodes:** capacity 1 (enforces one assignment per slot)
- **SlotCap → DayTier nodes:** cost = k² × scale, where k is the tier index for that day. First slot on a day is tier 0 (cheap), second is tier 1, etc.
- **DayTier → Sink:** capacity 1

The quadratic tier cost is the key insight: the solver minimizes total cost, so it strongly prefers spreading study blocks across many days rather than cramming one day. k=0 costs 0, k=1 costs 1, k=4 costs 16 — it becomes very expensive to add more blocks to an already-used day.

This beats a naive greedy approach (sort by deadline, fill earliest slots), which tends to front-load work and doesn't respect global balance.

---

## Architecture

### What is the high-level architecture?

Standard client-server, deployed on Vercel (frontend) + Render (backend) + Supabase (PostgreSQL in production):

```
Browser (React SPA)
    │  HTTPS / JSON
    ▼
Flask REST API  ──────────────────────────────────────┐
    │                                                  │
    ├── Auth (JWT + Google OAuth)                      │
    ├── Syllabus Parser (rule-based + OpenAI)          │
    ├── Scheduling Engine (MCMF)                       │
    ├── Calendar Service (Google Calendar API / iCal)  │
    └── Admin / Export                                 │
          │                                            │
          ▼                                            │
   MySQL / PostgreSQL  ◄──────────────────────────────┘
   (Users, Courses, Assignments, StudyTimes, CalendarEvents)
```

The backend is stateless (JWT-based, no server-side sessions), which makes horizontal scaling straightforward.

### How would you explain this to a non-technical person?

Think of it like a smart assistant for students. You hand it your class syllabus — it reads through the whole thing and pulls out every homework, project, and exam. Then it looks at your calendar (when your classes meet, what events you already have), and asks: "How late do you like to study? Do you prefer not to study on weekends?" Then it builds a schedule for you: "On Tuesday the 10th, study for CS for 2 hours; on Thursday, work on your English paper for 1.5 hours." You see it before it's set, can tweak it, and then it syncs straight to your Google Calendar.

### What are the tradeoffs in your design?

**MCMF vs. greedy/heuristic scheduling:**
- Pro: Globally optimal — finds the schedule that minimizes total "load" imbalance across all days simultaneously
- Con: O(flow × E log V) — can be slow for very large terms (~100 assignments × 5000 slots). In practice it's fast enough (<1s for typical terms), but it wouldn't scale to real-time scheduling for thousands of concurrent users without caching or precomputation.

**Hybrid parsing (rule-based + LLM):**
- Pro: Rules are fast, deterministic, free. LLM handles the long tail of weird syllabus formats.
- Con: LLM is slow (~2-4s), expensive per call, and non-deterministic. We mitigate with fallback logic and a confidence score so users know when to double-check.

**Preview/commit pattern for scheduling:**
- Pro: User sees proposed schedule before anything is written to DB. Dry-run uses SQLAlchemy session rollback — clean implementation.
- Con: Running the full MCMF twice (preview + confirm) doubles computation. Acceptable now, wasteful at scale.

**Cascading deletes (hard delete, no soft delete):**
- Pro: Simple, no orphaned data.
- Con: No undo. Deleting a term wipes everything. At scale, you'd want soft deletes and an archival system.

**Single-tenant JWT with per-query user_id filtering:**
- Pro: Simple, correct, no data leaks between users.
- Con: No row-level security at the DB layer. If a SQL injection were introduced, the app layer filtering wouldn't save you. Ideally you'd use DB-level RLS (Supabase/Postgres supports this).

---

## Your Contribution

### What did you specifically build?

I was primarily responsible for the **scheduling engine** and backend infrastructure:

- Designed and implemented the min-cost max-flow scheduling algorithm in `scheduling_service.py` — the flow network structure, node/edge construction, the successive shortest path solver, and the post-flow trimming step for weekly hour caps
- Introduced **slot-cap nodes** (commit `65f886d`) to enforce one-assignment-per-slot as a graph invariant rather than a post-hoc check — this was what enabled distinct per-course colors working correctly
- Built the Supabase migration to move from local MySQL to PostgreSQL in production
- Set up the CI pipeline: GitHub Actions, Ruff linting, pytest with coverage
- Contributed to the calendar integration (iCal parsing, Google Calendar event import, busy-slot logic in the scheduler)
- Fixed the per-course weekly cap bug where the cap was defined but the scheduler was ignoring it entirely

### What parts were most challenging?

Getting the flow network right. The conceptual structure is clean — source → assignments → slots → sink — but translating that into correct edge indexing with reverse edges, and then extracting which slots got assigned to which assignments from the residual graph, took multiple iterations. The subtle bugs were:

1. Off-by-one in reverse edge tracking that caused incorrect flow values
2. Slots being double-assigned before slot-cap nodes were introduced
3. The day-tier cost scaling — too low and the algorithm just picks the same day repeatedly; too high and it refuses to schedule more than 1 block per day even when necessary

The post-flow trimming (per-course cap enforcement) was also non-trivial: after the optimal flow, you have to decide which blocks to drop without breaking the relative priority of assignments. We sort by due date ascending and drop from the "least urgent" end — but that only works if the schedule is already balanced, which MCMF guarantees.

### What decisions did you personally make?

- **Quadratic vs. linear tier costs:** Linear (cost = k) didn't spread load well enough — the solver would pack 3 blocks in one day before moving to another day, because the marginal cost of tier 3 over tier 0 was only 3×. Quadratic (cost = k²) made the 3rd-block cost 9×, strongly discouraging stacking. That change noticeably improved schedule quality.
- **Slot-cap node architecture:** The original design had slot nodes go directly to tier nodes with cap=1. That worked for single-assignment use but broke down when I needed to guarantee color consistency. Adding a dedicated SlotCap layer made the invariant explicit and cleaned up the flow extraction logic.
- **Preview mode via rollback, not shadow tables:** Some designs use a temp table or a "draft" flag. I used SQLAlchemy's `session.rollback()` after extracting flow results — no extra schema complexity.

---

## Challenges

### What was the hardest bug or issue?

The slot-cap double-assignment bug. The original implementation had slot nodes with capacity 1, which I thought would prevent two assignments from using the same 15-minute slot. But two assignments could both send flow *to* the same slot node (cap 1 outflow), without violating any single edge capacity, because the slot→tier edge was where the bottleneck was — not the assignment→slot edges. The slot node could accept multiple inbound flow units as long as it forwarded exactly 1 to the tier. This meant two assignments would both "claim" the same slot in the flow, but the extraction step would only surface one of them, dropping the other silently. Adding slot-cap nodes (a second bottleneck on the inbound side) fixed this — now each slot can only receive 1 unit of flow total.

### What didn't work initially?

The per-course weekly hour cap. We had `study_hours_per_week` on the `Course` model from the beginning, but the scheduler didn't enforce it — it just generated however many hours the assignments needed. Users would get a schedule with 20+ hours of one course in a week. The fix was a post-flow pass: after extracting all scheduled blocks, group by (course, ISO week), compute total hours, and drop the lowest-priority blocks until within cap.

### What did you have to redesign?

The parsing confidence score. Originally it was a binary "parsed successfully / failed." We redesigned it as a 0-100 score based on heuristics: Did we find a course code? Assignments with due dates? Meeting times? Hours estimates? Each field that successfully parsed contributes to the score. The frontend uses this to show a warning banner ("Low confidence — please review carefully") below a threshold of ~60. This was a better UX signal than a binary flag.

---

## Scalability

### What would break if this had 10,000 users?

1. **Scheduling engine — O(n³) per request:** MCMF runs synchronously in the API request. With 10k users all generating schedules concurrently, the server would saturate. The fix is to push schedule generation into a background job queue (Celery + Redis/RabbitMQ) and poll for completion. Return a task ID immediately, frontend polls or uses websocket.

2. **Single database write path:** All study time writes go through one SQLAlchemy session. At scale, connection pool exhaustion is the first thing that breaks. You'd partition by user_id, use read replicas for GET-heavy endpoints (schedule view, dashboard), and write only to primary.

3. **Parsing service — OpenAI API calls:** LLM parsing is synchronous and expensive. At 10k users uploading syllabi, you'd hit OpenAI rate limits and latency spikes. Fix: queue syllabus parse jobs, return immediately with "processing" status, use webhook/websocket when done.

4. **File storage:** Avatar/banner uploads go to local disk (`/uploads/`). On a multi-instance deployment, uploaded files wouldn't be shared. You'd move to object storage (S3/GCS) immediately.

5. **JWT without a revocation store:** Stateless JWT is fast, but if a user gets compromised, you can't invalidate their token until it expires (7 days). At scale you'd add a Redis-backed token blocklist for explicit logouts and security events.

### How would you scale this system?

Short term (10k–100k users):
- Move schedule generation to Celery workers, decoupled from the API server
- Add Redis for session caching, rate limiting shared state, and job queue
- Switch file uploads to S3
- Add DB read replicas; annotate read-only queries to use them
- CDN for the static React frontend (already on Vercel, this is handled)

Medium term (100k–1M users):
- Partition the scheduling engine: shard users by ID across worker pools
- Consider pre-warming: when a user edits an assignment, queue a background re-generation so the schedule is ready when they open the calendar page
- Cache rendered study times per term with an invalidation strategy (any assignment edit invalidates)
- Rate limit the LLM parsing path more aggressively; add a tier system (free = rule-based only, pro = LLM)

Long term:
- If the MCMF becomes a bottleneck, explore approximate algorithms (LP relaxation, or ML-based schedule prediction trained on past user schedules)
- Event-driven architecture: assignment updated → event → scheduler worker → push update to client via websocket

### What bottlenecks exist?

1. **MCMF solver:** Synchronous, CPU-bound, O(n³). Fine for <100 assignments; degrades at scale.
2. **OpenAI parsing:** Network-bound, costly, non-deterministic latency.
3. **Google Calendar sync:** External API with rate limits (10k req/day default quota). At scale, need per-user token buckets and exponential backoff.
4. **DB connection pool:** Default SQLAlchemy pool of 5 connections. Fine for dev, not for 10k concurrent users.
5. **No caching layer:** Every dashboard load, every schedule view hits the DB. A Redis cache for hot reads (active term's study times, upcoming assignments) would dramatically reduce DB load.

---

## Improvement

### What would you improve if you had more time?

1. **Async schedule generation:** Job queue (Celery) so the API returns immediately with a task ID instead of blocking 1-2 seconds per generation.

2. **Smarter hour estimation:** Right now we use LLM or manual user input for hours. Better approach: let users rate how long assignments actually took, then train a lightweight regression model on historical data to predict future estimates. Cold-start with LLM, warm up with personal history.

3. **Incremental re-scheduling:** When one assignment changes, re-running the full MCMF is wasteful. You could do a local repair pass — only reschedule the affected assignment's blocks — using the existing solution as a warm start.

4. **Soft deletes + audit trail:** Currently deleting a term wipes everything. I'd add `deleted_at` timestamps and an archive pattern so users can recover deleted courses.

5. **Row-level security:** Move multi-tenant isolation from the application layer to the database layer (PostgreSQL RLS). More defense-in-depth.

6. **Push notifications:** Remind users when a study block is coming up (30 min before), or when an assignment is due and no study time has been scheduled for it.

### What would you redesign from scratch?

The parsing pipeline. The hybrid rule-based + LLM approach works, but the rules are fragile — each new syllabus format potentially breaks them. I'd replace the rule layer with a structured extraction approach using OpenAI function calling (or Anthropic's tool use): define a typed schema for what you want to extract, and let the model fill it in. This removes brittle regex, handles formatting variance naturally, and still gives you structured output. The fallback LLM call becomes the primary call; rules become validation guards.

I'd also redesign the calendar event model. Right now timed events, all-day events, and recurring events each have conditional column presence in the same table. A cleaner design would use a proper inheritance pattern or separate tables with a shared `calendar_events_base` and specialized `timed_event`, `all_day_event`, `recurring_event` tables joined via a discriminator column.

---

## Syllabify-Specifics (Quick-Hit Answers)

### "How does it work?"

You upload a PDF syllabus. The backend extracts all the assignments, due dates, and class meeting times using a mix of pattern matching and an LLM. You review the parsed data, edit anything that's wrong, then hit confirm. The backend runs a min-cost max-flow algorithm to figure out the globally optimal spread of study blocks across your semester — balancing workload across days, respecting your calendar, and not front-loading everything. You see a preview, approve it, and it syncs to your Google Calendar.

### "What's the hardest part?"

The scheduling algorithm. Greedy doesn't work — it stacks work on early days and leaves later days open for no reason. MCMF finds the global optimum by framing the problem as a flow network: assignments are supply nodes, time slots are demand nodes, and the cost structure (quadratic day-load tiers) encodes the "spread evenly" preference. Getting the flow network right, especially the slot-cap node layer and correctly extracting the assignment-to-slot mapping from the residual graph, took the most iteration.

### "What would you improve?"

Move schedule generation to an async job queue — right now it blocks the HTTP request, which is fine for a school project but would be the first thing to break under real load. I'd also replace the rule-based parser with structured LLM extraction using tool/function calling, which would be more robust to syllabus format variety. And I'd add soft deletes — right now if you delete a course, it's gone.

### "What challenges did you face?"

Three main ones:

1. **Double-assignment bug:** Two assignments were claiming the same 15-minute slot because the original graph structure let multiple flow units pass through a slot node. Fixed by introducing slot-cap nodes as an explicit bottleneck.

2. **Weekly cap not enforced:** The per-course study hour cap existed in the data model but the scheduler was ignoring it. The fix required a post-flow trimming pass that respects assignment priority (keep blocks for earlier-due assignments when trimming).

3. **Parsing variability:** Syllabi come in every format imaginable. Our rule-based parser worked on ~70% of test cases, but edge cases (non-standard date formats, assignments listed in narrative prose) required falling back to the LLM. Managing that hybrid reliably and returning a useful confidence signal to the user was an ongoing refinement.

---

## TikTok Social Graph Connections

This role is about graph systems at scale — here are the bridges worth drawing:

- **MCMF is a graph algorithm.** The scheduling problem is literally a flow network. I built the graph from scratch: adjacency list representation, residual edges, Bellman-Ford for potential initialization, Dijkstra with reduced costs for successive shortest paths. Directly relevant to working on graph infrastructure.

- **Flow/capacity modeling** is the same abstraction used in social graph problems: user-follower edges, feed ranking, notification routing all involve flow-like reasoning about capacity and load distribution.

- **Scalability of graph computation** is the same challenge. MCMF is O(n³) for dense graphs; real social graphs have billions of edges. The solution at TikTok scale is the same in principle — shard the graph, run distributed shortest-path computations, cache hot subgraphs. I've thought about this problem at the small scale; I'm ready to think about it at the large one.

- **Multi-tenant data isolation** maps to follower/following access control in social graphs — ensuring user A can only see content they're allowed to see is the same trust boundary problem.
