import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white">
      <header className="bg-gradient-to-r from-blue-900 via-blue-800 to-blue-700 shadow-lg">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex items-center justify-between">
            <div className="text-lg font-semibold tracking-tight text-white">
              Syllabify
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="rounded-button bg-white px-4 py-2 text-sm font-medium text-blue-900 no-underline hover:bg-blue-50"
              >
                Log in
              </Link>
              <button
                type="button"
                className="rounded-button bg-white px-4 py-2 text-sm font-medium text-blue-900 no-underline hover:bg-blue-50"
              >
                Sign up
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 pb-16 pt-10">
        <section className="rounded-3xl border border-blue-900/40 bg-blue-950/40 p-8 sm:p-12 shadow-xl shadow-blue-900/30">
          <p className="text-sm uppercase tracking-[0.2em] text-blue-300">
            Academic planning, made simple
          </p>
          <h1 className="mt-3 text-3xl sm:text-4xl md:text-5xl font-serif font-semibold text-white">
            Turn syllabi into a balanced study plan.
          </h1>
          <p className="mt-4 max-w-2xl text-base sm:text-lg text-blue-200">
            Syllabify helps you translate course expectations into a weekly
            schedule you can trust.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <div className="rounded-full bg-blue-900/60 px-4 py-2 text-sm text-blue-100">
              PDF and text syllabi
            </div>
            <div className="rounded-full bg-blue-900/60 px-4 py-2 text-sm text-blue-100">
              Manual review and edits
            </div>
            <div className="rounded-full bg-blue-900/60 px-4 py-2 text-sm text-blue-100">
              Calendar-ready schedule
            </div>
          </div>
        </section>

        <section className="mt-10 grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl border border-blue-900/40 bg-blue-950/40 p-5 shadow-lg shadow-blue-900/20">
            <h2 className="text-base font-semibold text-white">Structured intake</h2>
            <p className="mt-2 text-sm text-blue-200">
              Upload a syllabus and see the extracted assignments, exams, and milestones.
            </p>
          </div>
          <div className="rounded-2xl border border-blue-900/40 bg-blue-950/40 p-5 shadow-lg shadow-blue-900/20">
            <h2 className="text-base font-semibold text-white">Planning</h2>
            <p className="mt-2 text-sm text-blue-200">
              Review and adjust the data before a schedule is generated.
            </p>
          </div>
          <div className="rounded-2xl border border-blue-900/40 bg-blue-950/40 p-5 shadow-lg shadow-blue-900/20">
            <h2 className="text-base font-semibold text-white">Ready to export</h2>
            <p className="mt-2 text-sm text-blue-200">
              Send your plan to Google Calendar or download an ICS file.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
