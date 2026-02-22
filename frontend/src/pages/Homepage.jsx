import { Link } from 'react-router-dom';
import logo from '../assets/syllabify-logo-green.png';
import ThemeToggle from '../components/ThemeToggle';

export default function Home() {
  return (
    <div className="min-h-screen bg-surface text-ink">
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
                className="text-center rounded-button bg-accent px-3 py-1.5 text-sm font-medium text-white no-underline hover:bg-accent-hover transition-colors duration-200"
              >
                Log in
              </Link>
              <button
                type="button"
                className="rounded-button border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink no-underline hover:bg-surface-muted transition-colors duration-200"
              >
                Sign up
              </button>
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
                className="rounded-button bg-accent px-4 py-2.5 text-sm font-medium text-white no-underline hover:bg-accent-hover transition-colors duration-200 animate-fade-in [animation-delay:100ms]"
              >
                Log in
              </Link>
              <button
                type="button"
                className="rounded-button border border-border bg-surface px-4 py-2.5 text-sm font-medium text-ink no-underline hover:bg-surface-muted transition-colors duration-200 animate-fade-in [animation-delay:400ms]"
              >
                Sign up
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 pb-12 sm:pb-16 pt-8 sm:pt-10">
        <section className="rounded-3xl border border-border bg-surface-elevated p-6 sm:p-12 shadow-card">
          <p className="text-sm uppercase tracking-[0.2em] text-accent animate-fade-in-up">
            Academic planning, made simple
          </p>
          <h1 className="mt-3 text-3xl sm:text-4xl md:text-5xl font-serif font-semibold text-ink animate-fade-in-up [animation-delay:100ms]">
            Turn syllabi into a balanced study plan.
          </h1>
          <p className="mt-4 max-w-2xl text-base sm:text-lg text-ink-muted animate-fade-in-up [animation-delay:400ms]">
            Syllabify helps you translate course expectations into a weekly
            schedule you can trust.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <div className="rounded-full bg-accent-muted px-4 py-2 text-sm text-accent animate-fade-in-up [animation-delay:300ms]">
              PDF and text syllabi
            </div>
            <div className="rounded-full bg-accent-muted px-4 py-2 text-sm text-accent animate-fade-in-up [animation-delay:400ms]">
              Manual review and edits
            </div>
            <div className="rounded-full bg-accent-muted px-4 py-2 text-sm text-accent animate-fade-in-up [animation-delay:500ms]">
              Calendar-ready schedule
            </div>
          </div>
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-border bg-surface-elevated p-5 shadow-card animate-fade-in-up transition-transform duration-200 ease-out hover:scale-[1.02] hover:shadow-dropdown">
            <h2 className="text-base font-semibold text-ink">
              Structured intake
            </h2>
            <p className="mt-2 text-sm text-ink-muted">
              Upload a syllabus and see the extracted assignments, exams, and
              milestones.
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-surface-elevated p-5 shadow-card animate-fade-in-up transition-transform duration-200 ease-out hover:scale-[1.02] hover:shadow-dropdown [animation-delay:160ms]">
            <h2 className="text-base font-semibold text-ink">Planning</h2>
            <p className="mt-2 text-sm text-ink-muted">
              Review and adjust the data before a schedule is generated.
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-surface-elevated p-5 shadow-card animate-fade-in-up transition-transform duration-200 ease-out hover:scale-[1.02] hover:shadow-dropdown [animation-delay:320ms]">
            <h2 className="text-base font-semibold text-ink">
              Ready to export
            </h2>
            <p className="mt-2 text-sm text-ink-muted">
              Send your plan to Google Calendar or download an ICS file.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
