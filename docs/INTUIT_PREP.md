# Syllabify — Intuit Recruiter Interview Prep

> **Format:** Read this as a mental model — answer naturally, don't recite. This is conversational, not technical.  
> **Audience:** Recruiter (non-engineer or semi-technical). Focus on clarity, teamwork, and impact.

---

## The 60-Second Pitch

> *Use this when they ask "Tell me about a project you're proud of" or "Walk me through Syllabify."*

Syllabify is a web app that solves a real student problem: you get a syllabus PDF at the start of the semester, but it doesn't tell you *when* to actually study. So students either procrastinate or pull all-nighters.

Our app lets you upload your syllabus, it automatically reads through and pulls out all your assignments and deadlines, estimates how long each one will take, and then builds you a personalized study schedule across your entire semester — factoring in your class times, your other calendar events, and your preferences like "I don't want to study after 10pm."

The schedule shows up on a calendar in the app, and you can export it straight to Google Calendar.

I built it as a team of four for my Software Methodologies class. My main contributions were the scheduling algorithm and backend infrastructure.

---

## Explaining the Project Simply

### "What problem does it solve?"

Students get syllabi but have no system for when to actually sit down and do the work. Canvas and Google Calendar track deadlines — they don't help you plan. We close that gap.

### "What does it actually do, step by step?"

1. You upload a PDF syllabus (or paste text from Canvas)
2. The app reads it and pulls out: all assignments, their due dates, your class meeting times, and estimates of how long each task will take
3. You review that parsed data on screen and fix anything that looks off
4. You hit "Generate Schedule" — the system figures out the best spread of study blocks across your whole semester
5. You see a preview calendar before anything is saved — you can approve, tweak, or regenerate
6. Once you approve, it writes everything to your calendar and you can export to Google Calendar or download an iCal file

### "How is this different from just using Google Calendar?"

Google Calendar requires you to manually enter every study block yourself. That might be 30–40 events per course, per semester. We automate that entire process — including deciding *how much time* to put before each deadline.

### "What tech did you use?"

Simple version: Python backend (Flask), React frontend, a SQL database (PostgreSQL), and a little bit of AI (OpenAI) for reading confusing syllabus formats.

---

## Your Role and Contributions

### "What did you specifically work on?"

My main areas:

1. **The scheduling algorithm** — this is the core engine that decides when to study. I designed and built it from scratch. The trick was making it spread work evenly across days instead of cramming everything right before deadlines.

2. **Backend infrastructure** — set up the CI/CD pipeline (automated testing and deployment), migrated our database to production (Supabase/PostgreSQL), and contributed to the calendar sync features.

3. **Bug fixing** — caught and fixed a few subtle bugs: one where two assignments were getting scheduled in the same 15-minute slot, and one where a per-course study cap that was supposed to limit how many hours per week you'd study for one class was silently being ignored.

### "What were you most proud of?"

The scheduling algorithm. The naive approach — just fill in study time as early as possible before each deadline — produces terrible schedules. You'd end up with 6 hours of studying on one Tuesday and nothing on Friday.

I built a graph-based optimization approach where the system explicitly penalizes stacking too many study blocks on the same day. The result is a much more balanced, realistic schedule. Getting that right required a lot of iteration, but the output quality difference was noticeable.

### "What was hard?"

There was a subtle bug where two different assignments could both claim the same 15-minute time slot. The algorithm thought it was assigning them to different slots, but they were the same one. It was a graph structure issue — the way I'd set up the flow network allowed two "claims" on one slot to coexist. I found it by printing out the full schedule and noticing overlapping blocks. The fix was adding an explicit bottleneck node in the graph that enforced the one-assignment-per-slot rule at the data structure level, not just in post-processing.

---

## Team and Collaboration

### "How did you work as a team?"

Four people, roughly split ownership:

- One person: syllabus parsing and LLM integration
- One person: frontend (React, calendar UI, upload flow)
- One person: auth, user profiles, and admin interface
- Me: scheduling engine, backend infrastructure, calendar export

We had weekly syncs and used GitHub for everything — branches, pull requests, code review. Early on we defined clear contracts between components (what data the parser would return, what format the scheduler expected), which prevented a lot of integration headaches later.

### "Were there any team challenges?"

The integration between the parser and the scheduler. The parser returns "estimated hours" per assignment, which the scheduler depends on. We initially had loose assumptions about what that field would look like (could be null, could be a string, could be in minutes or hours). When we actually integrated them end-to-end, we had to clean up those contracts. It was a good lesson in defining precise interfaces between components early.

---

## AI Usage — Honest Breakdown

*Recruiters and Intuit interviewers may ask about this. Be transparent and specific.*

### AI built INTO the product

**OpenAI GPT-5 nano for syllabus parsing:**

Syllabi come in every format imaginable. Our rule-based approach (pattern matching and regex) worked for clean, structured PDFs but struggled with narrative-style syllabi or unusual date formats.

We added an optional LLM layer: if the rule-based parser returns low-confidence results, we send the syllabus text to OpenAI with a structured JSON schema and ask it to extract assignments, dates, and meeting times in a specific format.

- We use JSON Schema mode (OpenAI's strict output format) so the response is always valid JSON — no parsing of the LLM's raw text.
- Every extracted field gets a confidence score from 0 to 1.
- The UI shows a warning to the user if overall confidence is below ~60%, prompting them to review carefully.
- The LLM layer is off by default (controlled by an environment variable) — rule-based first, AI as fallback.

**What we accepted from the AI output:**  
The structured data directly — course code, assignment titles, due dates, estimated hours. We validated the schema on the backend before writing to the database.

**What we changed:**  
We wrote the system prompt ourselves and iterated on it significantly. Early drafts had the model hallucinating assignments that weren't in the syllabus. We added explicit instructions like "Do NOT invent data — use null if a field is unclear" and "Filter out non-assessment content like grade scale tables and policy text." The confidence scoring logic was also ours — we designed what "high confidence" means for each field type.

---

### AI used DURING development (Claude Code / GitHub Copilot)

I used Claude Code (Anthropic's AI coding assistant) throughout development. Here's how I actually used it:

**What I used AI for:**
- Boilerplate and scaffolding — setting up Flask blueprints, SQLAlchemy model templates, initial React component structure
- Debugging help — describing a bug and asking for hypotheses (especially for the slot-double-assignment issue)
- Syntax lookups — Python `zoneinfo`, SQLAlchemy 2.0 async patterns, iCalendar spec
- Code review — asking "what could go wrong with this?" on pieces I wasn't sure about
- Writing the initial structure of the min-cost max-flow solver, which I then significantly modified

**What I modified or rewrote:**
- The MCMF solver's core logic — the initial AI-generated version used a basic Bellman-Ford approach. I changed it to Dijkstra with Johnson's potentials (faster for dense graphs) and restructured the flow network to add slot-cap nodes and the quadratic day-tier cost model. These design decisions were mine.
- The confidence scoring system — the AI gave me a starting point but the field-by-field heuristics (what evidence raises or lowers confidence) were designed and tuned by me.
- The post-flow trimming pass for weekly course caps — I wrote this entirely myself after debugging the issue.

**What I accepted mostly as-is:**
- Utility functions (e.g., converting time strings to UTC, PDF text extraction helpers)
- Some boilerplate models and route decorators
- Parts of the calendar export service (iCal formatting)

**The honest bottom line:**  
AI accelerated the parts I already understood (scaffolding, lookups, boilerplate). For the core algorithmic work, it gave me a starting point I then redesigned. I wouldn't have shipped the scheduling engine without understanding every line — there were too many subtle bugs that required knowing *why* the graph was structured a certain way to diagnose.

---

## Common Recruiter Questions

### "Why Intuit?"

Intuit builds tools that help people with money — tax, accounting, financial planning. That's software with real stakes for real people. I care about building things that solve actual problems (Syllabify came from a real frustration I had as a student), and Intuit's products have that same quality. I'm also interested in how AI is being applied to financial tools — things like automatically categorizing transactions or surfacing insights from spending patterns feel like the same kind of "read messy input, extract structured value" problem I worked on with syllabi.

### "What do you bring to a team?"

I'm good at owning a slice of a system end-to-end — designing it, building it, debugging it, and explaining it to teammates. On Syllabify, I was the person who could tell you exactly why the scheduler was producing a weird output at 11pm the night before a deadline. I also care a lot about clean code and clear contracts between components, which saved us a lot of integration headaches.

### "What are your areas for growth?"

I want to get better at frontend — my strong suit is backend and algorithms, and while I contributed to the frontend on this project, I relied more heavily on my teammates there. I'm also still building intuition for production-scale systems. I've thought through scalability for Syllabify, but I haven't had to actually operate a system under real traffic. I want that experience.

### "Tell me about a time you dealt with ambiguity."

The parsing problem was ambiguous by nature — every syllabus is different. We didn't know upfront which rules to write or how to handle the long tail. My approach: build the most common case first (standard PDF structure), measure where it failed, and add targeted handling. When we hit a format that was too unpredictable for rules, that was the signal to bring in the LLM as a fallback. I prefer shipping something that works for 80% of cases and expanding from there, rather than trying to design for every edge case upfront.

---

## If They Ask You to Explain Code

### The scheduling algorithm (non-technical)

Imagine you have a list of study tasks, each with a deadline and an estimated number of hours. You also have a calendar showing when you're busy (classes, events, sleep). The naive approach is just to fill in study time as early as possible before each deadline — but that tends to pile up everything on the first available days and leave later days empty.

My approach models this as an optimization problem. Think of available time slots as seats on a train. Each assignment needs to "buy" a certain number of seats before its deadline. The ticket prices (costs) are structured so that buying a second seat on the same day costs more than buying a first seat — and buying a third costs even more. So the algorithm naturally spreads purchases across different days because that's the cheapest option. The result is a balanced schedule.

### The parsing pipeline (non-technical)

Syllabi are messy documents. Some list assignments in a table, some bury them in paragraphs, some use non-standard date formats. We handle this in two layers:

First, we run pattern matching — essentially, we look for things that look like due dates, assignment names, and time patterns. This works well for structured syllabi and is fast and free.

If that doesn't work well (the confidence score is low), we send the text to an AI model with a structured questionnaire: "Find me all the assignments. For each one, give me the name, due date, estimated hours, and your confidence that you found it correctly." The AI fills in the form. We validate the answers before trusting them.

### JWT authentication (non-technical)

When you log in, the server generates a signed "ticket" (a JSON Web Token) and sends it to your browser. Every time you make a request, you show that ticket. The server can verify the ticket is real without keeping a database of logged-in users — the signature proves it came from us. Tickets expire after 7 days, so if someone steals your ticket, it eventually becomes worthless.

---

## Quick Stats to Remember

- **Team size:** 4 people
- **Timeline:** ~3.5 months (Jan–Apr 2026)
- **Commits:** 250+
- **Stack:** React + Flask + PostgreSQL + OpenAI API
- **My main areas:** Scheduling engine, backend infrastructure, CI/CD, calendar sync, bug fixes
- **Deployed to:** Vercel (frontend) + Render (backend) + Supabase (database)
