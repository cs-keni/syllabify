/**
 * Privacy Policy page. Required for Google OAuth consent screen.
 */
import { Link } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle';

export default function Privacy() {
  return (
    <div className="min-h-screen bg-surface text-ink">
      <header className="border-b border-border bg-surface-elevated">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link
            to="/"
            className="text-lg font-semibold text-ink no-underline hover:text-accent"
          >
            Syllabify
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 sm:px-6 py-8 sm:py-12">
        <h1 className="text-2xl font-serif font-semibold text-ink">
          Privacy Policy
        </h1>
        <p className="mt-2 text-sm text-ink-muted">Last updated: March 2025</p>

        <div className="mt-8 space-y-6 text-sm text-ink leading-relaxed">
          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              1. Overview
            </h2>
            <p>
              Syllabify (&quot;we,&quot; &quot;our,&quot; or &quot;us&quot;) is
              an academic planning tool that helps students turn syllabi into
              study schedules. This policy describes how we collect, use, and
              protect your information.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              2. Information We Collect
            </h2>
            <p className="mb-2">We collect information you provide directly:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>
                <strong>Account data:</strong> Username, email (if provided),
                and password hash when you create an account.
              </li>
              <li>
                <strong>Google Sign-In:</strong> If you sign in with Google, we
                receive your email, name, and profile picture from Google. We do
                not store your Google password.
              </li>
              <li>
                <strong>Calendar data:</strong> If you connect Google Calendar,
                we read your calendar events to avoid scheduling conflicts. We
                store event titles, start/end times, and calendar IDs. We do not
                modify your Google Calendar.
              </li>
              <li>
                <strong>Syllabus data:</strong> Content you upload (PDFs, text)
                and the assignments, due dates, and courses we extract from
                them.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              3. How We Use Your Information
            </h2>
            <p>
              We use your information to provide and improve Syllabify: to
              create and manage your account, parse syllabi, generate schedules,
              import calendar events for conflict avoidance, and display your
              data back to you. We do not sell your data to third parties.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              4. Data Storage and Security
            </h2>
            <p>
              Your data is stored on our servers. We use industry-standard
              practices to protect your information, including encryption in
              transit (HTTPS) and hashed passwords. Calendar and syllabus data
              are associated with your account and accessible only to you.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              5. Third-Party Services
            </h2>
            <p>
              We use Google OAuth for sign-in and Google Calendar API for
              calendar import. Your use of these features is subject to
              Google&apos;s Privacy Policy. We only request the scopes necessary
              for these features (email, profile, calendar read-only).
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              6. Your Rights
            </h2>
            <p>
              You may access, correct, or delete your account and data through
              the app or by contacting us. You may disconnect Google Calendar at
              any time. Deleting your account will remove your data from our
              systems.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              7. Contact
            </h2>
            <p>
              For questions about this policy, contact us at the support email
              shown on the OAuth consent screen.
            </p>
          </section>
        </div>

        <p className="mt-10">
          <Link to="/" className="text-accent hover:underline text-sm">
            ← Back to home
          </Link>
        </p>
      </main>
    </div>
  );
}
