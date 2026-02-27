/**
 * Catches React errors and shows a friendly fallback with Retry.
 */
import { Component } from 'react';

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-[50vh] flex flex-col items-center justify-center p-8 bg-surface">
          <h1 className="text-xl font-semibold text-ink mb-2">
            Something went wrong
          </h1>
          <p className="text-sm text-ink-muted mb-6 text-center max-w-md">
            An unexpected error occurred. Try refreshing the page or going back.
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="rounded-button bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
            >
              Retry
            </button>
            <a
              href="/app"
              className="rounded-button border border-border px-4 py-2 text-sm font-medium text-ink hover:bg-surface-muted no-underline"
            >
              Back to Dashboard
            </a>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
