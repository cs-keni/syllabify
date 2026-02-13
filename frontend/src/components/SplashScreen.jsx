/**
 * Initial-load splash screen. Shows a creative loader, fades out when app is ready.
 * Only visible on first page load (while auth initializes); in-app navigation never triggers it.
 */
export default function SplashScreen({ exiting, onTransitionEnd }) {
  return (
    <div
      className={`fixed inset-0 z-[100] flex flex-col items-center justify-center bg-surface ${
        exiting ? 'animate-fade-out' : 'animate-fade-in'
      }`}
      onAnimationEnd={exiting ? onTransitionEnd : undefined}
    >
      {/* Modern circular loader: partial ring that rotates */}
      <div className="relative h-20 w-20">
        <svg className="h-full w-full animate-spin-slow" viewBox="0 0 64 64">
          <circle
            cx="32"
            cy="32"
            r="26"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            className="text-accent-muted/30"
          />
          <circle
            cx="32"
            cy="32"
            r="26"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray="82 163"
            strokeDashoffset="0"
            className="text-accent origin-center -rotate-90"
          />
        </svg>
      </div>
      <p className="mt-6 text-sm font-medium text-ink-muted tracking-wider uppercase">
        Syllabify
      </p>
    </div>
  );
}
