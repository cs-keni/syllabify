/**
 * Schedule page. Displays calendar via AppCalendar (FullCalendar).
 * Supports Google Calendar and ICS feed import, sources sidebar.
 */
import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../api/client';
import AppCalendar from '../components/AppCalendar';
import UnifiedImportModal from '../components/UnifiedImportModal';

export default function Schedule() {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();

  const [generating, setGenerating] = useState(false);
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);

  const [activeTerm, setActiveTerm] = useState(null);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [studyTimes, setStudyTimes] = useState([]);
  const [sources, setSources] = useState([]);
  const [syncingId, setSyncingId] = useState(null);
  const [popover, setPopover] = useState(null); // { studyTime, x, y }

  // Handle OAuth callback params
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

  // Load initial data
  useEffect(() => {
    if (!token) return;
    api.getCalendarStatus(token).then(d => setCalendarConnected(d.connected));
    api.getTerms().then(d => {
      const t = d.terms || [];
      setActiveTerm(t.find(x => x.is_active) || t[0]);
    });
  }, [token]);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [eventsData, sourcesData] = await Promise.all([
        api.getCalendarEvents(token, {}),
        api.getCalendarSources(token),
      ]);
      setCalendarEvents(eventsData.events || []);
      setSources(sourcesData.sources || []);
    } catch {
      // silently fail on initial load
    }

    if (activeTerm?.id) {
      try {
        const stData = await api.getStudyTimes(token, activeTerm.id);
        setStudyTimes(stData.study_times || []);
      } catch {
        // study times may not exist yet
      }
    }
  }, [token, activeTerm]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Handlers
  const handleConnectOrImport = async () => {
    if (!token) return toast.error('Please sign in first.');
    const status = await api.getCalendarStatus(token).catch(() => ({ connected: false }));
    if (!status.connected) {
      const { url } = await api.getCalendarAuthUrl(token);
      window.location.href = url;
      return;
    }
    setShowImportModal(true);
  };

  const handleImportGoogle = async (payload) => {
    await api.importCalendar(token, payload);
    toast.success('Calendar imported.');
    setCalendarConnected(true);
    fetchData();
  };

  const handleImportIcs = async (payload) => {
    const data = await api.importIcsFeed(token, payload);
    toast.success(`Imported ${data.imported_count ?? 0} event(s).`);
    fetchData();
  };

  const handleSyncSource = async (sourceId) => {
    setSyncingId(sourceId);
    try {
      const data = await api.syncSource(token, sourceId);
      toast.success(`Synced ${data.synced_count ?? 0} event(s).`);
      fetchData();
    } catch (err) {
      toast.error(err.message || 'Sync failed');
    } finally {
      setSyncingId(null);
    }
  };

  const handleDeleteSource = async (sourceId) => {
    try {
      await api.deleteCalendarSource(token, sourceId);
      toast.success('Source removed.');
      fetchData();
    } catch (err) {
      toast.error(err.message || 'Delete failed');
    }
  };

  const handleStudyTimeMove = async ({ props, start, end }) => {
    if (props?.type !== 'study_time' || !props?.data?.id) return;
    const studyTimeId = props.data.id;

    setStudyTimes(prev =>
      prev.map(st =>
        st.id === studyTimeId
          ? {
              ...st,
              start_time: start.toISOString(),
              end_time: end.toISOString(),
              is_locked: true,
            }
          : st
      )
    );

    try {
      await api.updateStudyTime(token, studyTimeId, {
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        is_locked: true,
      });
      toast.success('Study block pinned.');
    } catch (err) {
      toast.error(err.message || 'Could not move study block');
      fetchData();
    }
  };

  const handleStudyTimeClick = ({ type, data }, jsEvent) => {
    if (type !== 'study_time' || !data) return;
    setPopover({
      studyTime: data,
      x: jsEvent?.clientX ?? 0,
      y: jsEvent?.clientY ?? 0,
    });
  };

  const handleToggleLock = async () => {
    if (!popover?.studyTime) return;
    const studyTime = popover.studyTime;
    const nextLocked = !studyTime.is_locked;
    setPopover(null);

    try {
      await api.updateStudyTime(token, studyTime.id, { is_locked: nextLocked });
      setStudyTimes(prev =>
        prev.map(st => (st.id === studyTime.id ? { ...st, is_locked: nextLocked } : st))
      );
      toast.success(nextLocked ? 'Study block locked.' : 'Study block unlocked.');
    } catch (err) {
      toast.error(err.message || 'Failed to update study block');
      fetchData();
    }
  };

  const handleGenerateStudyTimes = async () => {
    if (!token) return toast.error('Please sign in to generate study times.');
    setGenerating(true);
    try {
      const { terms } = await api.getTerms();
      const active = terms?.find(t => t.is_active) || terms?.[0];
      if (!active?.id) {
        toast.error('No term selected. Create or select a term from the dashboard.');
        return;
      }
      const data = await api.generateStudyTimes(token, active.id);
      toast.success(
        data.created_count !== undefined
          ? `Generated ${data.created_count} study time block(s).`
          : 'Study times generated.'
      );
      fetchData();
    } catch (err) {
      toast.error(err.message || 'Failed to generate study times.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="animate-fade-in">
        <Link
          to="/app"
          className="text-sm text-ink-muted hover:text-ink transition-colors no-underline"
        >
          &larr; Dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-ink">Schedule</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Your calendar events and study blocks at a glance.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleGenerateStudyTimes}
            disabled={generating || !token}
            className="px-4 py-2 rounded-lg bg-primary text-primary-inv font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {generating ? 'Generating\u2026' : 'Generate Study Times'}
          </button>
          <button
            type="button"
            onClick={handleConnectOrImport}
            disabled={!token}
            className="px-4 py-2 rounded-lg border border-border bg-surface text-ink font-medium text-sm hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            Import Calendar
          </button>
          <button
            type="button"
            disabled
            title="Coming soon"
            className="px-4 py-2 rounded-lg border border-border bg-surface text-ink-muted font-medium text-sm opacity-50 cursor-not-allowed"
          >
            iCal Export
          </button>
        </div>
      </div>

      {showImportModal && (
        <UnifiedImportModal
          onClose={() => setShowImportModal(false)}
          onImportGoogle={handleImportGoogle}
          onImportIcs={handleImportIcs}
          token={token}
          getCalendarList={api.getCalendarList}
          calendarConnected={calendarConnected}
          activeTerm={activeTerm}
        />
      )}

      <div className="flex gap-6">
        {/* Main calendar */}
        <div className="flex-1 min-w-0">
          <AppCalendar
            calendarEvents={calendarEvents}
            studyTimes={studyTimes}
            onEventDrop={handleStudyTimeMove}
            onEventResize={handleStudyTimeMove}
            onEventClick={handleStudyTimeClick}
          />
          {popover && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setPopover(null)}
              />
              <div
                className="fixed z-50 min-w-[180px] rounded-lg border border-border bg-surface p-3 text-sm shadow-lg"
                style={{ top: popover.y + 8, left: popover.x + 8 }}
              >
                <p className="mb-1 truncate font-medium text-ink">
                  {popover.studyTime.course_name || 'Study Block'}
                </p>
                <p className="mb-2 text-xs text-ink-muted">
                  {popover.studyTime.is_locked ? 'Locked (pinned)' : 'Unlocked (will regenerate)'}
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleToggleLock}
                    className="flex-1 rounded bg-primary px-2 py-1 text-xs font-medium text-primary-inv hover:opacity-90"
                  >
                    {popover.studyTime.is_locked ? 'Unlock' : 'Lock'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setPopover(null)}
                    className="rounded border border-border px-2 py-1 text-xs text-ink-muted hover:text-ink"
                  >
                    Close
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Sources sidebar */}
        <div className="w-64 shrink-0 hidden lg:block">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
              Sources
            </h3>
            {sources.length === 0 ? (
              <p className="text-xs text-gray-500">No sources yet. Import a calendar to get started.</p>
            ) : (
              <ul className="space-y-2">
                {sources.map((src) => (
                  <li key={src.id} className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: src.color }}
                      />
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">
                          {src.source_label}
                        </p>
                        <p className="text-[10px] text-gray-400">
                          {src.event_count} events &middot; {src.source_type === 'google' ? 'Google' : 'ICS'}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button
                        onClick={() => handleSyncSource(src.id)}
                        disabled={syncingId === src.id}
                        title="Sync"
                        className="text-gray-400 hover:text-blue-600 text-xs disabled:opacity-50"
                      >
                        {syncingId === src.id ? '\u21BB' : '\u21BB'}
                      </button>
                      <button
                        onClick={() => handleDeleteSource(src.id)}
                        title="Remove"
                        className="text-gray-400 hover:text-red-600 text-xs"
                      >
                        &times;
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <button
              onClick={handleConnectOrImport}
              className="mt-3 w-full text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              + Add Source
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
