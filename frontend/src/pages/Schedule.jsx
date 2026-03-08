/**
 * Schedule page. Displays weekly schedule via SchedulePreview.
 * Google Calendar import and sync.
 */
import { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../api/client';
import SchedulePreview from '../components/SchedulePreview';
import CalendarImportModal from '../components/CalendarImportModal';

/** Monday of the given week. */
function getMonday(d) {
  const x = new Date(d);
  const day = x.getDay();
  const diff = x.getDate() - day + (day === 0 ? -6 : 1);
  x.setDate(diff);
  x.setHours(0, 0, 0, 0);
  return x;
}

/** Renders schedule page with weekStart (Monday of current week) and SchedulePreview. */
export default function Schedule() {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const [generating, setGenerating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [terms, setTerms] = useState([]);
  const [activeTerm, setActiveTerm] = useState(null);
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()));
  const scheduleRefreshRef = useRef(null);

  useEffect(() => {
    if (searchParams.get('calendar_connected') === '1') {
      toast.success('Google Calendar connected.');
      setCalendarConnected(true);
      window.history.replaceState({}, '', '/app/schedule');
    }
    if (searchParams.get('calendar_error')) {
      toast.error('Failed to connect Google Calendar. Try again.');
      window.history.replaceState({}, '', '/app/schedule');
    }
  }, [searchParams]);

  useEffect(() => {
    if (!token) return;
    api.getCalendarStatus(token).then(d => setCalendarConnected(d.connected));
    api.getTerms().then(d => {
      const t = d.terms || [];
      setTerms(t);
      setActiveTerm(t.find(x => x.is_active) || t[0]);
    });
  }, [token]);

  const handleConnectOrImport = async () => {
    if (!token) {
      toast.error('Please sign in first.');
      return;
    }
    const status = await api
      .getCalendarStatus(token)
      .catch(() => ({ connected: false }));
    if (!status.connected) {
      const { url } = await api.getCalendarAuthUrl(token);
      window.location.href = url;
      return;
    }
    setShowImportModal(true);
  };

  const handleImport = async payload => {
    await api.importCalendar(token, payload);
    toast.success('Calendar imported.');
    setCalendarConnected(true);
  };

  const handleSync = async () => {
    if (!token) return;
    setSyncing(true);
    try {
      const data = await api.syncCalendar(token);
      toast.success(`Synced ${data.synced_count ?? 0} event(s).`);
    } catch (err) {
      toast.error(err.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

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
        toast.error(
          'No term selected. Create or select a term from the dashboard.'
        );
        return;
      }
      const data = await api.generateStudyTimes(token, activeTerm.id);
      toast.success(
        data.created_count !== undefined
          ? `Generated ${data.created_count} study time block(s).`
          : 'Study times generated.'
      );
      scheduleRefreshRef.current?.();
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
          Weekly view of your study blocks.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() =>
                setWeekStart(d => {
                  const next = new Date(d);
                  next.setDate(next.getDate() - 7);
                  return getMonday(next);
                })
              }
              className="rounded-button border border-border px-2 py-1.5 text-sm text-ink-muted hover:text-ink hover:bg-surface-muted"
              aria-label="Previous week"
            >
              ←
            </button>
            <span className="text-sm text-ink px-2 min-w-[140px] text-center">
              {weekStart.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}{' '}
              –{' '}
              {new Date(
                weekStart.getTime() + 6 * 24 * 60 * 60 * 1000
              ).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
            <button
              type="button"
              onClick={() =>
                setWeekStart(d => {
                  const next = new Date(d);
                  next.setDate(next.getDate() + 7);
                  return getMonday(next);
                })
              }
              className="rounded-button border border-border px-2 py-1.5 text-sm text-ink-muted hover:text-ink hover:bg-surface-muted"
              aria-label="Next week"
            >
              →
            </button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleGenerateStudyTimes}
            disabled={generating || !token}
            className="px-4 py-2 rounded-lg bg-primary text-primary-inv font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {generating ? 'Generating…' : 'Generate study times'}
          </button>
          <button
            type="button"
            onClick={handleConnectOrImport}
            disabled={!token}
            className="px-4 py-2 rounded-lg border border-border bg-surface text-ink font-medium text-sm hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {calendarConnected
              ? 'Import from Google Calendar'
              : 'Connect Google Calendar'}
          </button>
          {calendarConnected && (
            <button
              type="button"
              onClick={handleSync}
              disabled={syncing || !token}
              className="px-4 py-2 rounded-lg border border-border bg-surface text-ink font-medium text-sm hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            >
              {syncing ? 'Syncing…' : 'Sync'}
            </button>
          )}
        </div>
      </div>
      {showImportModal && (
        <CalendarImportModal
          onClose={() => setShowImportModal(false)}
          onImport={handleImport}
          token={token}
          getCalendarList={api.getCalendarList}
          activeTerm={activeTerm}
        />
      )}
      <SchedulePreview
        weekStart={weekStart}
        activeTerm={activeTerm}
        token={token}
        getStudyTimes={api.getStudyTimes}
        onRefresh={scheduleRefreshRef}
      />
    </div>
  );
}
