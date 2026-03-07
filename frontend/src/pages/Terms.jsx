/**
 * Terms of Service page. Required for Google OAuth consent screen.
 */
import { Link } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle';

export default function Terms() {
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
          Terms of Service
        </h1>
        <p className="mt-2 text-sm text-ink-muted">Last updated: March 2025</p>

        <div className="mt-8 space-y-6 text-sm text-ink leading-relaxed">
          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              1. Acceptance
            </h2>
            <p>
              By using Syllabify, you agree to these Terms of Service. If you do
              not agree, do not use the service.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              2. Description of Service
            </h2>
            <p>
              Syllabify is an academic planning tool that helps students upload
              syllabi, extract assignments and due dates, and generate study
              schedules. It may integrate with Google Calendar to import
              existing events and avoid scheduling conflicts.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              3. Your Responsibilities
            </h2>
            <p>
              You are responsible for the accuracy of the content you upload and
              for maintaining the security of your account. Do not share your
              credentials. You agree to use Syllabify only for lawful purposes
              and in accordance with your institution&apos;s academic integrity
              policies.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              4. Intellectual Property
            </h2>
            <p>
              Syllabify and its content are owned by us or our licensors. You
              retain ownership of the syllabus content you upload. By uploading
              content, you grant us a license to process and display it for the
              purpose of providing the service.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              5. Disclaimer
            </h2>
            <p>
              Syllabify is provided &quot;as is.&quot; We do not guarantee the
              accuracy of parsed syllabus data or generated schedules. Always
              verify important dates and assignments against your official
              course materials.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              6. Limitation of Liability
            </h2>
            <p>
              To the extent permitted by law, we are not liable for any
              indirect, incidental, or consequential damages arising from your
              use of Syllabify.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              7. Changes
            </h2>
            <p>
              We may update these terms from time to time. Continued use of the
              service after changes constitutes acceptance of the updated terms.
            </p>
          </section>

          <section>
            <h2 className="text-base font-semibold text-ink mb-2">
              8. Contact
            </h2>
            <p>
              For questions about these terms, contact us at the support email
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
