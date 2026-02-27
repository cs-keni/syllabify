# Quality of Life — Feature Brainstorm

**Status: Implemented (Feb 2025).** All planned QOL features from the priority list have been implemented. The remaining items in sections 1–20 are a **living brainstorm** for future iterations (global search, PWA, notifications, 2FA, collaboration, etc.). Add new ideas as we discover them—implement when ready.

Ideas to improve the Syllabify user experience. Think from both a **user perspective** (what would make my life easier?) and an **expert engineer** lens (what patterns, polish, and delight matter?).

---

## 1. Layout & Visual Polish

- **Full-width layouts** — Remove arbitrary `max-w-xl` constraints where content feels cramped (e.g. Preferences). Use responsive grids to fill space meaningfully.
- **Two-column layouts** — On larger screens: Account | Study preferences side-by-side instead of stacked.
- **Empty states** — Every list/section should have a helpful empty state: illustration, copy, and a clear CTA (e.g. "No assignments yet. Upload a syllabus or add one manually.").
- **Skeleton loaders** — Replace generic "Loading…" spinners with content-shaped skeletons (cards, rows) so the layout doesn't jump.
- **Consistent spacing** — Use a design token system (e.g. 4, 8, 12, 16, 24, 32px) for padding/margin.
- **Visual hierarchy** — Clear section headers, subtle dividers, card shadows to indicate depth.
- **Micro-animations** — Stagger list item appearance, button hover states, toast slide-ins.
- **Progress indicators** — Show completion % per course or term (e.g. "3 of 12 assignments done").

---

## 2. Navigation & Discovery

- **Breadcrumbs** — On Course page: Dashboard → Winter 2026 → CS 422. Helps users orient.
- **Back button consistency** — Every inner page should have a predictable "← Back" that goes to the logical parent.
- **Keyboard shortcuts** — e.g. `?` for help overlay, `n` for new course, `u` for upload, `Esc` to close modals.
- **Global search** — Search across courses and assignments by name. Fuzzy matching.
- **Quick switcher** — Cmd/Ctrl+K opens a command palette: jump to course, navigate to page, run action.
- **Sticky headers** — On long pages (e.g. Course with many assignments), keep the course name and primary actions visible on scroll.
- **Recently viewed** — Show last 3–5 courses on Dashboard or in a sidebar for quick access.

---

## 3. Profile & Personalization

- **Profile picture / avatar upload** — Upload image or use gravatar from email. Display in header.
- **Display name** — Optional friendly name (e.g. "Alex") separate from login username.
- **Timezone** — Store user timezone for due dates and scheduling. Default to browser-detected.
- **Theme persistence** — Remember dark/light preference in localStorage + backend.
- **Accent color picker** — Let users choose their accent (blue, purple, green, etc.).
- **Font size** — Small / Medium / Large option for readability.
- **Reduce motion** — Respect `prefers-reduced-motion` and disable animations.
- **Notification preferences** — Toggle email reminders, in-app toasts, browser push.

---

## 4. Course & Assignment UX

- **Per-course colors** — Assign a color to each course (for calendar, dashboard, badges). User picks from palette.
- **Drag-and-drop reorder** — Reorder assignments within a course (e.g. by priority or chronology).
- **Bulk actions** — Select multiple assignments → delete, change due date, or change type in one go.
- **Due date presets** — "Next Monday", "End of term", "Two weeks from now" for quick entry.
- **Assignment templates** — Save common patterns (e.g. "Weekly Reading", "Lab Report") and add with one click.
- **Inline date picker** — Calendar popover instead of raw `type="date"` for better UX.
- **Conflict detection** — Warn when assignment due date clashes with another or with meeting times.
- **Duplicate assignment** — "Copy" button to clone an assignment and tweak.
- **Notes per assignment** — Optional rich-text or markdown notes (e.g. "Focus on Ch. 5–7").
- **Subtasks / checklist** — Break assignment into sub-items (e.g. "Read", "Outline", "Write", "Revise").

---

## 5. Upload & Parse

- **Drag-and-drop file upload** — Drop zone for PDF/DOCX instead of only file picker.
- **Parse history** — "Recently parsed" list: last 5 syllabi with quick "Use again" or "Update course".
- **Confidence display** — Visual indicator (color, icon) for low vs high confidence parses. Suggest manual review when low.
- **Batch upload** — Upload multiple syllabi at once → parse all → review each in sequence.
- **OCR for scanned PDFs** — Fallback for image-based PDFs that don't have selectable text.
- **Parse progress** — Progress bar or stages ("Extracting text…" → "Identifying assignments…" → "Done") for long parses.
- **Manual override** — When parse misses something, "Add from snippet" with paste-and-parse already exists; extend to "Add from file snippet" (select region of PDF).

---

## 6. Dashboard & Overview

- **Upcoming assignments** — Real list when scheduler exists. Sort by due date, show next 5–7.
- **Course quick stats** — Per course: total hours, assignments due this week, completion %.
- **Customizable layout** — Let user reorder or collapse sections (This week, Upcoming, Courses).
- **Recent activity** — "You added 3 assignments to CS 422 yesterday" or "Parsed syllabus for CS 433".
- **Onboarding checklist** — First-time: "Add a term → Upload syllabus → Add course" steps with checkmarks.
- **Sample/demo data** — Optional "Try with sample data" for new users to explore.
- **Weekly summary card** — "You have 12 hours of work scheduled this week across 4 courses."

---

## 7. Schedule & Calendar (post-scheduler)

- **Visual week view** — Hourly grid with blocks for study sessions and meetings.
- **Month view** — Calendar heat map or list of due dates.
- **Color by course** — Each course gets a color in the schedule.
- **Click to add** — Click empty slot → "Add study block" or "Add assignment".
- **Drag to reschedule** — Drag assignment blocks to new times.
- **Print-friendly view** — Clean, printable weekly schedule.
- **Export to calendar** — ICS export (when implemented) for Google Calendar, Outlook, Apple.

---

## 8. Notifications & Reminders

- **Email reminders** — "CS 422 Exam 1 due in 3 days" (configurable: 1 day, 3 days, 1 week before).
- **In-app notifications** — Bell icon with list of upcoming due dates and actionable links.
- **Digest** — Weekly email: "Your week ahead: 5 assignments due, 12 hours scheduled."
- **Browser push** — Optional push notifications for due-date reminders.
- **Quiet hours** — Don't send reminders between X p.m. and Y a.m. (user-configurable).

---

## 9. Accessibility

- **Screen reader labels** — All interactive elements have `aria-label` or visible text.
- **Focus management** — Modals trap focus; closing returns focus to trigger. Skip-to-content link.
- **High contrast mode** — Toggle or respect `prefers-contrast`.
- **Font scaling** — Support user font size preferences (rem-based, no fixed px for text).
- **Keyboard navigation** — Full tab order, no mouse-only interactions.
- **Reduced motion** — Disable or simplify animations when user prefers.
- **Error announcements** — Form errors announced to screen readers.

---

## 10. Performance & Reliability

- **Optimistic updates** — When adding/editing assignment, update UI immediately; rollback on API error.
- **Undo** — After delete: "Undo" toast for 5 seconds to restore.
- **Retry on failure** — Automatic retry for failed API calls (with exponential backoff).
- **Offline support (PWA)** — Cache critical data; show cached view when offline; queue writes for sync.
- **Data export** — Export all courses/assignments as JSON or CSV for backup or migration.
- **Import** — Import from JSON/CSV or from other tools (e.g. Notion, Todoist).
- **Session management** — "Active sessions" in settings: see devices, revoke sessions.

---

## 11. Mobile

- **Touch-friendly targets** — Buttons and links at least 44×44px.
- **Swipe actions** — Swipe left on assignment row for Edit/Delete.
- **Bottom nav** — On phones, bottom navigation for main tabs (Dashboard, Upload, Schedule, Profile).
- **Responsive forms** — Stack inputs on narrow screens; full-width inputs.
- **Pull to refresh** — Pull down on Dashboard to refresh courses and upcoming.
- **Haptic feedback** — Light haptic on key actions (success, error).

---

## 12. Data & Privacy

- **Account deletion** — Self-service: "Delete my account" with confirmation. Cascade delete all data.
- **Data export (GDPR)** — "Download my data" → ZIP with JSON of all user data.
- **Activity log** — "Recent account activity" (logins, security changes) for transparency.
- **Password change** — In Preferences: change password with current password verification.
- **Two-factor auth (2FA)** — Optional TOTP for extra security.

---

## 13. Onboarding & Help

- **First-time tour** — Step-through: "This is your Dashboard. Add a term, then upload a syllabus."
- **Tooltips** — Contextual tooltips on first visit (dismissible).
- **Help center / FAQ** — In-app or link to docs: common questions, how to upload, how scheduling works.
- **What's new** — Changelog or "What's new" modal after updates.
- **Sample data** — "Load sample course" for new users to explore.
- **Video walkthrough** — Short embedded video for Upload flow.

---

## 14. Power User / Advanced

- **Bulk edit modal** — Select multiple assignments → edit due date, hours, or type in one form.
- **CSV import** — Upload CSV with columns: course, name, due, hours, type.
- **Custom assignment types** — User-defined types beyond assignment/midterm/final/quiz/project.
- **API access** — Optional REST API key for power users / integrations.
- **Shortcuts overlay** — `?` key shows all keyboard shortcuts.
- **Copy share link** — Share read-only view of a course (e.g. for study group).

---

## 15. Collaboration (future)

- **Share course** — Share read-only view with link. Revocable.
- **Study groups** — Create group, add members, see shared assignments.
- **Notes** — Per-assignment or per-course notes visible to group.
- **Comments** — Comment on assignments (e.g. "Meeting moved to Thursday").

---

## 16. Delight & Polish

- **Celebration moments** — Subtle confetti or animation when user completes first upload, adds first assignment.
- **Easter eggs** — Fun small interactions (e.g. Konami code, hover effects).
- **Consistent empty state copy** — Friendly, actionable, not robotic.
- **Smooth transitions** — Page transitions, list reordering animations.
- **Sound** — Optional subtle sounds for success/error (off by default).
- **Personalized greeting** — "Good morning, Alex" or "Welcome back" on Dashboard.

---

## 17. Course Management & Organization

- **Archive past terms** — Hide (don't delete) old terms for reference. "View archived" to unhide.
- **Duplicate term** — Copy all courses and assignments from a previous term into a new one (e.g. "Copy Fall 2025 → Fall 2026").
- **Course templates** — Save a course structure (name, typical assignments) to create similar courses next term.
- **Filter & sort courses** — Sort by name, assignment count, or last updated. Filter by term.
- **Course description** — Optional notes field per course (e.g. "Professor Smith, MWF 10am").
- **Link to syllabus** — Store URL or attach original syllabus PDF for quick reference.

---

## 18. Smart Features & Insights

- **Workload balance** — Show hours per week distribution; highlight "heavy weeks" (e.g. "20+ hours the week of Mar 16").
- **Overdue highlight** — Past-due assignments in red or with strikethrough; "Overdue" badge.
- **"What's due this week" badge** — Count on nav or Dashboard header (e.g. "5 due this week").
- **Suggest study time** — Based on preferences + assignments, recommend when to block study.
- **Conflict warnings** — "You have 3 exams and 2 projects due the same week."
- **Date format preference** — MM/DD vs DD/MM vs "Mar 16, 2026" for locale.

---

## 19. Integrations & Import

- **LMS import** — Import from Canvas, Blackboard, or Moodle if user has export/API access.
- **Import from screenshot** — OCR a syllabus screenshot to extract assignments.
- **Export to PDF** — Generate printable weekly schedule or assignment list.
- **Link to materials** — Per assignment: optional URL to rubric, reading, or Drive folder.

---

## 20. Error Handling & Resilience

- **Friendly error page** — "Something went wrong" with Retry button and optional support contact.
- **Graceful degradation** — When API is slow, show cached/stale data with "Last updated X minutes ago" and refresh option.
- **Form validation feedback** — Inline validation as user types; clear error messages.
- **Offline banner** — "You're offline. Some features may not work." when navigator.onLine is false.
- **Session expiry handling** — When token expires mid-session, redirect to login with "Session expired. Please sign in again."

---

## Priority Matrix (suggested)

| High impact, low effort | High impact, high effort |
|------------------------|--------------------------|
| Full-width / two-column layouts | Global search |
| Empty states everywhere | Drag-and-drop reorder |
| Skeleton loaders | Undo after delete |
| Breadcrumbs | PWA / offline |
| Timezone support | Notifications (email) |
| Per-course colors | Bulk actions |
| Due date presets | Data export/import |

| Low impact, low effort | Low impact, high effort |
|------------------------|--------------------------|
| Accent color picker | 2FA |
| Tooltips | Collaboration features |
| Keyboard shortcuts | API access |
| Copy assignment | Video walkthrough |

---

*Add, remove, or reprioritize as the product evolves.*

---

## Implementation status (last audited: Feb 2025)

The following QOL features from this document have been implemented in the dev branch. No need to re-audit from scratch—treat this as the checkpoint. Remaining items are backlog for future iterations.

### Implemented

| Category | Feature |
|----------|---------|
| Layout & Visual | Empty states (No courses/assignments + CTA), skeleton loaders, card shadows, stagger animations |
| Navigation | Breadcrumbs (Dashboard → Term → Course), back button, keyboard shortcuts (?, g+d, g+u, g+s, g+p, Esc), shortcuts overlay (? key), sticky headers (course, nav), recently viewed (last 5 courses) |
| Profile | Theme persistence (light/dark in localStorage), reduce motion (prefers-reduced-motion) |
| Course & Assignment | Due date presets (Today, Tomorrow, Next Mon, +1 wk, +2 wks), duplicate assignment (Copy), overdue highlight (red + badge), sort courses (name/count), sort assignments |
| Schedule | Conflict highlighting (overlapping blocks in schedule view) |
| Upload & Parse | Drag-and-drop file upload, confidence display (score + label, low-confidence styling) |
| Dashboard | Personalized greeting (Good morning/afternoon/evening), course quick stats |
| Error & Resilience | ErrorBoundary with Retry, 401 handling + redirect, session expiry toast, offline banner |
| Accessibility | Skip-to-content link, prefers-reduced-motion |
| **New (Feb 2025)** | **Undo after delete**, **accent color picker**, **per-course colors**, **timezone**, **bulk delete** |

### Not yet implemented (future backlog)

Global search, PWA/offline support, data export, email notifications, two-factor auth, collaboration features, and other advanced items listed above.

---

*This document remains a living brainstorm. The above status reflects dev branch as of Feb 2025.*
