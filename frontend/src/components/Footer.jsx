/**
 * Minimal footer with Privacy and Terms links. Used on public pages.
 */
import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="mt-auto pt-8 pb-4 border-t border-border/50">
      <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-ink-muted">
        <Link to="/privacy" className="hover:text-ink transition-colors">
          Privacy Policy
        </Link>
        <span aria-hidden>·</span>
        <Link to="/terms" className="hover:text-ink transition-colors">
          Terms of Service
        </Link>
      </div>
    </footer>
  );
}
