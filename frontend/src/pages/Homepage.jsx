import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import logo from '../assets/syllabify-logo-green.png';
import ThemeToggle from '../components/ThemeToggle';
import Footer from '../components/Footer';
import * as api from '../api/client';
import { useAuth } from '../contexts/AuthContext';

const DEMO_BLOCKS = [
  { top: '8%', left: '2%', width: '18%', height: '10%', color: '#3B82F6', label: 'CS 422' },
  { top: '22%', left: '22%', width: '18%', height: '14%', color: '#10B981', label: 'MATH 341' },
  { top: '8%', left: '42%', width: '18%', height: '10%', color: '#F59E0B', label: 'CS 422' },
  { top: '38%', left: '2%', width: '18%', height: '18%', color: '#8B5CF6', label: 'ENGL 202' },
  { top: '52%', left: '62%', width: '18%', height: '14%', color: '#3B82F6', label: 'CS 422' },
  { top: '22%', left: '62%', width: '18%', height: '10%', color: '#10B981', label: 'MATH 341' },
  { top: '68%', left: '22%', width: '18%', height: '10%', color: '#F59E0B', label: 'CS 422' },
  { top: '38%', left: '82%', width: '16%', height: '18%', color: '#EC4899', label: 'BIO 110' },
];

const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI'];

function CalendarMockup() {
  return (
    <div className="rounded-xl border border-border bg-surface shadow-xl overflow-hidden select-none">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-surface-elevated">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-border/60" />
          <div className="w-16 h-3 rounded bg-border/60" />
        </div>
        <div className="flex gap-1.5">
          {['Month', 'Week', 'Day', 'List'].map(v => (
            <div
              key={v}
              className={`px-2 py-0.5 rounded text-[10px] font-medium ${v === 'Week' ? 'bg-accent text-white' : 'text-ink-muted bg-border/40'}`}
            >
              {v}
            </div>
          ))}
        </div>
      </div>
      {/* Day headers */}
      <div className="grid grid-cols-5 border-b border-border bg-surface-elevated">
        {DAYS.map(d => (
          <div key={d} className="py-1.5 text-center text-[10px] font-semibold text-ink-muted tracking-wider">
            {d}
          </div>
        ))}
      </div>
      {/* Calendar grid */}
      <div className="relative bg-surface" style={{ height: '200px' }}>
        {/* Column lines */}
        {[20, 40, 60, 80].map(p => (
          <div key={p} className="absolute top-0 bottom-0 border-l border-border/40" style={{ left: `${p}%` }} />
        ))}
        {/* Hour lines */}
        {[25, 50, 75].map(p => (
          <div key={p} className="absolute left-0 right-0 border-t border-border/30" style={{ top: `${p}%` }} />
        ))}
        {/* Study blocks */}
        {DEMO_BLOCKS.map((b, i) => (
          <div
            key={i}
            className="absolute rounded-md flex items-start px-1.5 pt-1 overflow-hidden shadow-sm"
            style={{
              top: b.top,
              left: b.left,
              width: b.width,
              height: b.height,
              backgroundColor: b.color,
              opacity: 0.88,
            }}
          >
            <span className="text-[9px] font-semibold text-white leading-tight truncate">
              📚 {b.label}
            </span>
          </div>
        ))}
        {/* Now indicator */}
        <div className="absolute left-0 right-0 border-t-2 border-red-500 z-10" style={{ top: '35%' }}>
          <div className="absolute -left-1 -top-1.5 w-2.5 h-2.5 rounded-full bg-red-500" />
        </div>
      </div>
    </div>
  );
}

const STEPS = [
  {
    num: '01',
    title: 'Upload your syllabus',
    desc: 'Drop a PDF or paste text. AI extracts every assignment, exam, and deadline automatically.',
    icon: '📄',
  },
  {
    num: '02',
    title: 'Review & confirm',
    desc: 'Edit anything the parser missed. Set study hours, adjust dates, and confirm your course data.',
    icon: '✏️',
  },
  {
    num: '03',
    title: 'Get a balanced schedule',
    desc: 'A scheduling algorithm spreads study blocks across your available time, avoiding class conflicts.',
    icon: '📅',
  },
];

const FEATURES = [
  { label: 'AI syllabus parsing', desc: 'GPT-5 nano extracts assignments, exams, and deadlines from any syllabus format.' },
  { label: 'Min-cost scheduling', desc: 'A graph-flow algorithm balances workload across your week, respecting your class times.' },
  { label: 'Google Calendar sync', desc: 'Import your existing events as conflicts and export your study plan as an iCal feed.' },
  { label: 'Live calendar view', desc: 'Drag to reschedule any block. Lock the ones you want to keep when regenerating.' },
];

export default function Home() {
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
  const [demoLoading, setDemoLoading] = useState(false);

  const handleDemoLogin = async () => {
    setDemoLoading(true);
    try {
      const data = await api.demoLogin();
      await loginWithToken(data.token);
      navigate('/app/schedule');
    } catch {
      alert('Demo login failed. Please try again.');
    } finally {
      setDemoLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface text-ink">
      <header className="border-b border-border bg-surface-elevated shadow-card">
        <div className="relative mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-1.5 sm:py-4">
          <div className="sm:hidden space-y-1.5">
            <div className="relative flex items-center justify-between gap-1.5">
              <div className="text-base font-semibold tracking-tight text-ink animate-fade-in">
                Syllabify
              </div>
              <ThemeToggle />
              <div className="pointer-events-none absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2">
                <img
                  src={logo}
                  alt="Syllabify"
                  className="h-40 w-40 object-contain animate-scale-in"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-1">
              <Link
                to="/login"
                className="text-center rounded-button bg-[#0F8A4C] px-3 py-1.5 text-sm font-medium text-white no-underline hover:bg-[#094728] transition-colors duration-200"
              >
                Log in
              </Link>
              <Link
                to="/register"
                className="text-center rounded-button border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink no-underline hover:bg-surface-muted transition-colors duration-200"
              >
                Sign up
              </Link>
            </div>
          </div>
          <div className="relative hidden sm:flex items-center justify-between gap-3">
            <div className="text-lg font-semibold tracking-tight text-ink animate-fade-in">
              Syllabify
            </div>
            <div className="pointer-events-none absolute left-1/2 -translate-x-1/2">
              <img
                src={logo}
                alt="Syllabify"
                className="h-28 w-28 md:h-40 md:w-40 lg:h-48 lg:w-48 object-contain animate-scale-in"
              />
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <ThemeToggle />
              <Link
                to="/login"
                className="rounded-button bg-[#0F8A4C] px-4 py-2.5 text-sm font-medium text-white no-underline hover:bg-[#094728] transition-colors duration-200 animate-fade-in [animation-delay:100ms]"
              >
                Log in
              </Link>
              <Link
                to="/register"
                className="rounded-button border border-border bg-surface px-4 py-2.5 text-sm font-medium text-ink no-underline hover:bg-surface-muted transition-colors duration-200 animate-fade-in [animation-delay:400ms]"
              >
                Sign up free
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 mx-auto w-full max-w-5xl px-4 sm:px-6 lg:px-8 pb-16 pt-8 sm:pt-12 space-y-16">

        {/* Hero */}
        <section className="grid lg:grid-cols-2 gap-10 items-center">
          <div className="animate-fade-in-up">
            <p className="text-sm uppercase tracking-[0.2em] text-accent font-medium mb-3">
              Academic planning, made simple
            </p>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-serif font-semibold text-ink leading-tight">
              Turn syllabi into a balanced study plan.
            </h1>
            <p className="mt-4 text-base sm:text-lg text-ink-muted max-w-lg">
              Upload a course syllabus. Syllabify extracts every deadline, estimates
              workload, and schedules study blocks around your existing calendar —
              automatically.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {['PDF & text syllabi', 'AI extraction', 'Conflict-aware scheduling', 'Google Calendar sync'].map(tag => (
                <span
                  key={tag}
                  className="rounded-full bg-accent-muted px-3 py-1.5 text-xs font-medium text-accent"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/register"
                className="rounded-button bg-[#0F8A4C] px-5 py-2.5 text-sm font-semibold text-white no-underline hover:bg-[#094728] transition-colors duration-200 shadow-sm"
              >
                Get started free
              </Link>
              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={demoLoading}
                className="rounded-button border border-border px-5 py-2.5 text-sm font-medium text-ink hover:bg-surface-muted transition-colors duration-200 disabled:opacity-60"
              >
                {demoLoading ? 'Loading…' : 'Try the demo →'}
              </button>
            </div>
          </div>
          <div className="animate-fade-in-up [animation-delay:200ms]">
            <CalendarMockup />
          </div>
        </section>

        {/* How it works */}
        <section className="animate-fade-in-up [animation-delay:100ms]">
          <h2 className="text-xl font-semibold text-ink mb-8 text-center">
            From syllabus to schedule in three steps
          </h2>
          <div className="grid gap-6 md:grid-cols-3">
            {STEPS.map(s => (
              <div
                key={s.num}
                className="rounded-2xl border border-border bg-surface-elevated p-6 shadow-card hover:shadow-dropdown transition-shadow duration-200"
              >
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl">{s.icon}</span>
                  <span className="text-xs font-bold tracking-widest text-ink-subtle uppercase">
                    Step {s.num}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-ink mb-2">{s.title}</h3>
                <p className="text-sm text-ink-muted leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Feature grid */}
        <section className="animate-fade-in-up [animation-delay:200ms]">
          <h2 className="text-xl font-semibold text-ink mb-8 text-center">
            Everything students actually need
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {FEATURES.map(f => (
              <div
                key={f.label}
                className="flex gap-4 rounded-xl border border-border bg-surface-elevated p-5 shadow-card hover:scale-[1.01] hover:shadow-dropdown transition-all duration-200"
              >
                <div className="mt-0.5 w-2 h-2 rounded-full bg-accent shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-ink mb-1">{f.label}</p>
                  <p className="text-xs text-ink-muted leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="rounded-3xl border border-border bg-surface-elevated p-8 sm:p-12 shadow-card text-center animate-fade-in-up">
          <h2 className="text-2xl sm:text-3xl font-serif font-semibold text-ink mb-3">
            Ready to stop guessing?
          </h2>
          <p className="text-sm sm:text-base text-ink-muted mb-6 max-w-md mx-auto">
            Create an account and upload your first syllabus in under two minutes.
            No credit card required.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              to="/register"
              className="rounded-button bg-[#0F8A4C] px-8 py-3 text-sm font-semibold text-white no-underline hover:bg-[#094728] transition-colors duration-200 shadow-sm"
            >
              Get started — it&apos;s free
            </Link>
            <button
              type="button"
              onClick={handleDemoLogin}
              disabled={demoLoading}
              className="rounded-button border border-border px-8 py-3 text-sm font-medium text-ink hover:bg-surface-muted transition-colors duration-200 disabled:opacity-60"
            >
              {demoLoading ? 'Loading…' : 'Try the demo →'}
            </button>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
