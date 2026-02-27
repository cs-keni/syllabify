/**
 * Schedule page. Displays weekly schedule via SchedulePreview.
 * DISCLAIMER: Project structure may change.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../api/client';
import SchedulePreview from '../components/SchedulePreview';

/** Renders schedule page with weekStart (Monday of current week) and SchedulePreview. */
export default function Schedule() {
  const { token } = useAuth();
  const [generating, setGenerating] = useState(false);

  const [weekStart] = useState(() => {
    const d = new Date();
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
  });

  const handleGenerateStudyTimes = async () => {
    if (!token) {
      toast.error('Please sign in to generate study times.');
      return;
    }
    setGenerating(true);
    try {
      const { terms } = await api.getTerms();
      const activeTerm = terms?.find(t => t.is_active) || terms?.[0];
      if (!activeTerm?.id) {
        toast.error('No term selected. Create or select a term from the dashboard.');
        return;
      }
      const data = await api.generateStudyTimes(token, activeTerm.id);
      toast.success(
        data.created_count !== undefined
          ? `Generated ${data.created_count} study time block(s).`
          : 'Study times generated.'
      );
    } catch (err) {
      toast.error(err.message || 'Failed to generate study times.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="animate-fade-in">
        <Link
          to="/app"
          className="text-sm text-ink-muted hover:text-ink transition-colors no-underline"
        >
          ← Dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-ink">Schedule</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Weekly view of your study blocks. Conflicts are highlighted subtly.
        </p>
        <button
          type="button"
          onClick={handleGenerateStudyTimes}
          disabled={generating || !token}
          className="mt-3 px-4 py-2 rounded-lg bg-primary text-primary-inv font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {generating ? 'Generating…' : 'Generate study times'}
        </button>
      </div>
      <SchedulePreview weekStart={weekStart} />
    </div>
  );
}
