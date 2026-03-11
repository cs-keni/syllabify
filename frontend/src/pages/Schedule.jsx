/**
 * Schedule page. Displays calendar via AppCalendar (FullCalendar).
 * Supports Google Calendar and ICS feed import, sources sidebar.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../api/client';
import AppCalendar from '../components/AppCalendar';
import UnifiedImportModal from '../components/UnifiedImportModal';

const SOURCE_COLOR_OPTIONS = [
  { hex: '#EF4444', label: 'Red' },
  { hex: '#F97316', label: 'Orange' },
  { hex: '#F59E0B', label: 'Amber' },
  { hex: '#84CC16', label: 'Lime' },
  { hex: '#10B981', label: 'Green' },
  { hex: '#14B8A6', label: 'Teal' },
  { hex: '#06B6D4', label: 'Cyan' },
  { hex: '#3B82F6', label: 'Blue' },
  { hex: '#6366F1', label: 'Indigo' },
  { hex: '#8B5CF6', label: 'Violet' },
  { hex: '#EC4899', label: 'Pink' },
  { hex: '#64748B', label: 'Slate' },
];

export default function Schedule() {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();

  const [generating, setGenerating] = useState(false);
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportFeedUrl, setExportFeedUrl] = useState('');
  const [exportEnabled, setExportEnabled] = useState(true);
  const [exportError, setExportError] = useState('');
  const [showProposedScheduleModal, setShowProposedScheduleModal] = useState(false);
  const [proposedSlots, setProposedSlots] = useState([]);
  const [applyingSchedule, setApplyingSchedule] = useState(false);

  const [activeTerm, setActiveTerm] = useState(null);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [studyTimes, setStudyTimes] = useState([]);
  const [sources, setSources] = useState([]);
  const [syncingId, setSyncingId] = useState(null);
  const [colorEditId, setColorEditId] = useState(null);
  const [popover, setPopover] = useState(null); // { studyTime, x, y }
  const [eventDetail, setEventDetail] = useState(null); // { event, x, y }
  const [hoverPreview, setHoverPreview] = useState(null); // { type, data, x, y }
  const hoverTimeoutRef = useRef(null);
  const autoSyncDone = useRef(false);

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
      } catch (err) {
        console.warn('Failed to fetch study times:', err?.message);
      }
    }
  }, [token, activeTerm]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-sync stale sources when schedule page loads (e.g. not synced in 6+ hours)
  useEffect(() => {
    if (!token || sources.length === 0 || autoSyncDone.current) return;
    const STALE_HOURS = 6;
    const staleSources = sources.filter(src => {
      const last = src.last_synced_at;
      if (!last) return true;
      const age = (Date.now() - new Date(last).getTime()) / (1000 * 60 * 60);
      return age >= STALE_HOURS;
    });
    if (staleSources.length > 0) {
      autoSyncDone.current = true;
      Promise.all(staleSources.map(src => api.syncSource(token, src.id)))
        .then(() => fetchData())
        .catch(() => {});
    }
  }, [token, sources, fetchData]);

  // Handlers
  const handleConnectOrImport = async () => {
    if (!token) return toast.error('Please sign in first.');
    const status = await api
      .getCalendarStatus(token)
      .catch(() => ({ connected: false }));
    setCalendarConnected(status.connected);
    if (!status.connected) {
      const { url } = await api.getCalendarAuthUrl(token);
      window.location.href = url;
      return;
    }
    setShowImportModal(true);
  };

  const handleImportGoogle = async payload => {
    await api.importCalendar(token, payload);
    toast.success('Calendar imported.');
    setCalendarConnected(true);
    fetchData();
  };

  const handleImportIcs = async payload => {
    const data = await api.importIcsFeed(token, payload);
    toast.success(`Imported ${data.imported_count ?? 0} event(s).`);
    fetchData();
  };

  const handleSyncSource = async sourceId => {
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

  const handleDeleteSource = async sourceId => {
    try {
      await api.deleteCalendarSource(token, sourceId);
      toast.success('Source removed.');
      fetchData();
    } catch (err) {
      toast.error(err.message || 'Delete failed');
    }
  };

  const handleColorChange = async (sourceId, color) => {
    setColorEditId(null);
    try {
      await api.updateCalendarSource(token, sourceId, { color });
      setSources(prev =>
        prev.map(s => (s.id === sourceId ? { ...s, color } : s))
      );
      setCalendarEvents(prev =>
        prev.map(e =>
          e.source_id === sourceId ? { ...e, source_color: color } : e
        )
      );
      toast.success('Color updated.');
    } catch (err) {
      toast.error(err.message || 'Failed to update color');
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

  const handleEventClickAll = ({ type, data }, jsEvent) => {
    setHoverPreview(null);
    const x = jsEvent?.clientX ?? 0;
    const y = jsEvent?.clientY ?? 0;
    if (type === 'study_time' && data) {
      setEventDetail(null);
      setPopover({ studyTime: data, x, y });
    } else if (type === 'calendar_event' && data) {
      setPopover(null);
      setEventDetail({ event: data, x, y });
    }
  };

  const handleEventHover = ({ type, data }, jsEvent) => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => {
      const x = jsEvent?.clientX ?? 0;
      const y = jsEvent?.clientY ?? 0;
      setHoverPreview({ type, data, x, y });
    }, 300);
  };

  const handleEventHoverEnd = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    setHoverPreview(null);
  };

  const handleToggleLock = async () => {
    if (!popover?.studyTime) return;
    const studyTime = popover.studyTime;
    const nextLocked = !studyTime.is_locked;
    setPopover(null);

    try {
      await api.updateStudyTime(token, studyTime.id, { is_locked: nextLocked });
      setStudyTimes(prev =>
        prev.map(st =>
          st.id === studyTime.id ? { ...st, is_locked: nextLocked } : st
        )
      );
      toast.success(
        nextLocked ? 'Study block locked.' : 'Study block unlocked.'
      );
    } catch (err) {
      toast.error(err.message || 'Failed to update study block');
      fetchData();
    }
  };

  const handleLockEntireDay = async () => {
    if (!popover?.studyTime || !token) return;
    const dayStart = new Date(popover.studyTime.start_time);
    const dayStr = dayStart.toISOString().slice(0, 10);
    const blocksOnDay = studyTimes.filter(st => {
      const d = new Date(st.start_time).toISOString().slice(0, 10);
      return d === dayStr && !st.is_locked;
    });
    setPopover(null);
    if (blocksOnDay.length === 0) {
      toast.info('All blocks on this day are already locked.');
      return;
    }
    try {
      await Promise.all(
        blocksOnDay.map(st => api.updateStudyTime(token, st.id, { is_locked: true }))
      );
      setStudyTimes(prev =>
        prev.map(st =>
          blocksOnDay.some(b => b.id === st.id) ? { ...st, is_locked: true } : st
        )
      );
      toast.success(`Locked ${blocksOnDay.length} block(s) for this day.`);
    } catch (err) {
      toast.error(err.message || 'Failed to lock day');
      fetchData();
    }
  };

  const handleGenerateStudyTimes = async () => {
    if (!token) return toast.error('Please sign in to generate study times.');
    setGenerating(true);
    try {
      let termToUse = activeTerm;
      if (!termToUse?.id) {
        const { terms } = await api.getTerms();
        termToUse = terms?.find(t => t.is_active) || terms?.[0];
      }
      if (!termToUse?.id) {
        toast.error(
          'No term selected. Create or select a term from the dashboard.'
        );
        return;
      }
      const data = await api.generateStudyTimes(token, termToUse.id, { preview: true });
      const slots = data.study_times || [];
      const count = data.created_count ?? slots.length;
      if (count === 0) {
        toast.info(
          'No study blocks to generate (assignments may have no workload or no available slots).'
        );
        return;
      }
      setProposedSlots(slots);
      setShowProposedScheduleModal(true);
    } catch (err) {
      toast.error(err.message || 'Failed to generate study times.');
    } finally {
      setGenerating(false);
    }
  };

  const handleApplyProposedSchedule = async () => {
    if (!token || !activeTerm?.id) return;
    setApplyingSchedule(true);
    try {
      const data = await api.generateStudyTimes(token, activeTerm.id, { preview: false });
      const count = data.created_count ?? 0;
      toast.success(
        count > 0
          ? `Applied ${count} study block(s). Use the calendar arrows to navigate to the weeks of your assignments to see them.`
          : 'Schedule applied.'
      );
      setShowProposedScheduleModal(false);
      setProposedSlots([]);
      fetchData();
    } catch (err) {
      toast.error(err.message || 'Failed to apply study schedule.');
    } finally {
      setApplyingSchedule(false);
    }
  };

  const handleOpenExportModal = async () => {
    if (!token) return toast.error('Please sign in first.');
    setShowExportModal(true);
    setExportLoading(true);
    setExportError('');
    setExportFeedUrl('');
    try {
      const data = await api.getIcalExportToken(token);
      setExportFeedUrl(data.feedUrl || '');
      setExportEnabled(data.enabled !== false);
    } catch (err) {
      setExportError(err.message || 'Failed to load iCal feed URL');
    } finally {
      setExportLoading(false);
    }
  };

  // Pie chart data: study time per course (minutes)
  const studyTimeByCourse = (() => {
    const byCourse = {};
    for (const st of studyTimes) {
      const name = st.course_name || 'Study';
      const start = new Date(st.start_time).getTime();
      const end = new Date(st.end_time).getTime();
      const mins = Math.round((end - start) / 60000);
      byCourse[name] = (byCourse[name] || 0) + mins;
    }
    return Object.entries(byCourse)
      .map(([name, mins]) => ({ name, mins }))
      .sort((a, b) => b.mins - a.mins);
  })();

  const totalStudyMins = studyTimeByCourse.reduce((s, x) => s + x.mins, 0);
  const PIE_COLORS = [ '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#64748B' ];

  const handleCopyExportUrl = async () => {
    if (!exportFeedUrl) return;
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(exportFeedUrl);
      } else {
        const el = document.createElement('textarea');
        el.value = exportFeedUrl;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
      }
      toast.success('Feed URL copied.');
    } catch {
      toast.error('Could not copy URL');
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
          Your calendar events and study blocks at a glance. Study blocks appear in the date range of your assignments—use the calendar arrows to navigate.
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
            {calendarConnected
              ? 'Import from Google Calendar'
              : 'Connect Google Calendar'}
          </button>
          <button
            type="button"
            onClick={handleOpenExportModal}
            disabled={!token}
            className="px-4 py-2 rounded-lg border border-border bg-surface text-ink font-medium text-sm hover:bg-surface-muted disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
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

      {showProposedScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/45"
            onClick={() => !applyingSchedule && setShowProposedScheduleModal(false)}
          />
          <div className="relative z-10 w-full max-w-xl rounded-xl border border-border bg-surface p-5 shadow-xl max-h-[85vh] flex flex-col">
            <h3 className="text-lg font-semibold text-ink">
              Proposed study schedule
            </h3>
            <p className="mt-1 text-sm text-ink-muted">
              Here&apos;s a proposed study schedule based on your availability, course workload, and calendar events. Unlocked blocks will be replaced when you apply.
            </p>
            <div className="mt-4 overflow-y-auto flex-1 min-h-0 rounded-lg border border-border bg-surface-muted/50 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-ink-muted mb-2">
                {proposedSlots.length} block(s) · spread across your study window
              </p>
              <ul className="space-y-1.5 text-sm">
                {proposedSlots.slice(0, 50).map((s, i) => (
                  <li key={i} className="flex items-center gap-2 text-ink">
                    <span className="font-medium truncate flex-1">
                      {s.course_name || 'Study'}
                    </span>
                    <span className="text-ink-muted shrink-0 font-mono text-xs">
                      {new Date(s.start_time).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}{' '}
                      {new Date(s.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}–{new Date(s.end_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                    </span>
                  </li>
                ))}
                {proposedSlots.length > 50 && (
                  <li className="text-ink-muted text-xs">
                    … and {proposedSlots.length - 50} more
                  </li>
                )}
              </ul>
            </div>
            <div className="mt-4 flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => setShowProposedScheduleModal(false)}
                disabled={applyingSchedule}
                className="rounded-lg border border-border px-3 py-2 text-sm font-medium text-ink hover:bg-surface-muted disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApplyProposedSchedule}
                disabled={applyingSchedule}
                className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-inv hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {applyingSchedule ? 'Applying…' : 'Apply schedule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/45"
            onClick={() => setShowExportModal(false)}
          />
          <div className="relative z-10 w-full max-w-xl rounded-xl border border-border bg-surface p-5 shadow-xl">
            <h3 className="text-lg font-semibold text-ink">iCal Export</h3>
            <p className="mt-1 text-sm text-ink-muted">
              Subscribe this private feed URL in Apple Calendar / Google
              Calendar.
            </p>

            {exportLoading ? (
              <p className="mt-4 text-sm text-ink-muted">Loading feed URL...</p>
            ) : exportError ? (
              <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {exportError}
              </p>
            ) : (
              <>
                <div className="mt-4 rounded-lg border border-border bg-surface-muted p-3">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-muted">
                    Your Feed URL
                  </p>
                  <p className="break-all text-xs text-ink">
                    {exportFeedUrl || 'No feed URL available'}
                  </p>
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={handleCopyExportUrl}
                    disabled={!exportFeedUrl}
                    className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-inv hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Copy URL
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowExportModal(false)}
                    className="rounded-lg border border-border px-3 py-2 text-xs font-medium text-ink hover:bg-surface-muted"
                  >
                    Close
                  </button>
                </div>
                <p className="mt-3 text-xs text-ink-muted">
                  {exportEnabled
                    ? 'Feed is enabled. Changes may take some time to appear in subscribed calendar apps.'
                    : 'Feed is currently disabled.'}
                </p>
              </>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main calendar */}
        <div className="flex-1 min-w-0 order-1">
          <AppCalendar
            calendarEvents={calendarEvents}
            studyTimes={studyTimes}
            onEventDrop={handleStudyTimeMove}
            onEventResize={handleStudyTimeMove}
            onEventClick={handleEventClickAll}
            onEventHover={handleEventHover}
            onEventHoverEnd={handleEventHoverEnd}
          />
          {hoverPreview && !popover && !eventDetail && (
            <div
              className="fixed z-50 min-w-[200px] max-w-[280px] rounded-lg border border-border bg-surface-elevated p-3 text-sm shadow-dropdown animate-fade-in-fast pointer-events-none"
              style={{
                top: Math.min(hoverPreview.y + 12, window.innerHeight - 180),
                left: Math.min(hoverPreview.x + 12, window.innerWidth - 300),
              }}
            >
              {hoverPreview.type === 'study_time' ? (
                <>
                  <p className="font-medium text-ink truncate">
                    {hoverPreview.data.course_name || 'Study Block'}
                  </p>
                  <p className="text-xs text-ink-muted mt-0.5">
                    {hoverPreview.data.is_locked ? 'Locked (kept when regenerating)' : 'Unlocked (replaced when regenerating)'} · Click to edit
                  </p>
                  {hoverPreview.data.start_time && (
                    <p className="text-xs text-ink-muted font-mono mt-1">
                      {new Date(hoverPreview.data.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} – {new Date(hoverPreview.data.end_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                    </p>
                  )}
                </>
              ) : (
                <>
                  <p className="font-medium text-ink truncate">
                    {hoverPreview.data.title}
                  </p>
                  {(hoverPreview.data.start_time || hoverPreview.data.start_date) && (
                    <p className="text-xs text-ink-muted font-mono mt-0.5">
                      {hoverPreview.data.start_date
                        ? `${hoverPreview.data.start_date}${hoverPreview.data.end_date ? ` – ${hoverPreview.data.end_date}` : ''}`
                        : `${new Date(hoverPreview.data.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} – ${new Date(hoverPreview.data.end_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`}
                    </p>
                  )}
                  {hoverPreview.data.location && (
                    <p className="text-xs text-ink-muted mt-0.5 truncate">
                      {hoverPreview.data.location}
                    </p>
                  )}
                  <p className="text-[10px] text-ink-subtle mt-1.5">Click to edit</p>
                </>
              )}
            </div>
          )}
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
                  {popover.studyTime.is_locked
                    ? 'Locked — this block stays when you regenerate.'
                    : 'Unlocked — will be replaced when you regenerate. Lock to keep it.'}
                </p>
                <div className="flex flex-col gap-1.5">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleToggleLock}
                      className="flex-1 rounded bg-primary px-2 py-1 text-xs font-medium text-primary-inv hover:opacity-90"
                      title={popover.studyTime.is_locked ? 'Unlock so it can be replaced' : 'Lock to keep this block'}
                    >
                      {popover.studyTime.is_locked ? 'Unlock' : 'Lock block'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setPopover(null)}
                      className="rounded border border-border px-2 py-1 text-xs text-ink-muted hover:text-ink"
                    >
                      Close
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={handleLockEntireDay}
                    className="w-full rounded border border-border px-2 py-1 text-xs text-ink-muted hover:bg-surface-muted hover:text-ink"
                    title="Lock all study blocks on this day at once"
                  >
                    Lock entire day
                  </button>
                </div>
              </div>
            </>
          )}
          {eventDetail && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setEventDetail(null)}
              />
              <div
                className="fixed z-50 w-80 max-h-[60vh] overflow-y-auto rounded-lg border border-border bg-surface p-4 text-sm shadow-lg"
                style={{
                  top: Math.min(eventDetail.y + 8, window.innerHeight - 320),
                  left: Math.min(eventDetail.x + 8, window.innerWidth - 340),
                }}
              >
                <p className="mb-1 font-semibold text-ink">
                  {eventDetail.event.title}
                </p>
                {eventDetail.event.event_category && (
                  <span className="mb-2 inline-block rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-ink-muted">
                    {eventDetail.event.event_category.replace('_', ' ')}
                  </span>
                )}
                {(eventDetail.event.start_date ||
                  eventDetail.event.start_time) && (
                  <p className="mt-2 text-xs text-ink-muted font-mono tabular-nums">
                    {eventDetail.event.start_date
                      ? `Date: ${eventDetail.event.start_date}`
                      : `${new Date(eventDetail.event.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} – ${new Date(eventDetail.event.end_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`}
                  </p>
                )}
                {eventDetail.event.location && (
                  <p className="mt-1 text-xs text-ink-muted">
                    Location: {eventDetail.event.location}
                  </p>
                )}
                {eventDetail.event.source_id != null && (
                  <div className="mt-3 pt-2 border-t border-border">
                    <p className="text-[10px] font-medium text-ink-muted mb-1.5 uppercase tracking-wide">Event color</p>
                    <p className="text-[10px] text-ink-muted mb-1.5">Changes all events from this source (e.g. this Google calendar).</p>
                    <div className="flex flex-wrap gap-1.5">
                      {SOURCE_COLOR_OPTIONS.map(({ hex, label }) => (
                        <button
                          key={hex}
                          type="button"
                          onClick={() => {
                            const src = sources.find(s => s.id === eventDetail.event.source_id);
                            if (src) handleColorChange(src.id, hex);
                          }}
                          className="w-6 h-6 rounded border border-border hover:scale-110 transition-transform"
                          style={{ backgroundColor: hex }}
                          title={label}
                        />
                      ))}
                    </div>
                  </div>
                )}
                {eventDetail.event.description && (
                  <div className="mt-2 whitespace-pre-wrap break-words text-xs text-ink leading-relaxed border-t border-border pt-2">
                    {eventDetail.event.description}
                  </div>
                )}
                {!eventDetail.event.description &&
                  !eventDetail.event.location && (
                  <p className="mt-2 text-xs text-ink-muted italic">
                    No additional details.
                  </p>
                )}
                <button
                  type="button"
                  onClick={() => setEventDetail(null)}
                  className="mt-3 w-full rounded border border-border px-2 py-1 text-xs text-ink-muted hover:text-ink"
                >
                  Close
                </button>
              </div>
            </>
          )}
        </div>

        {/* Sidebar: sources + pie chart */}
        <div className="w-full lg:w-64 shrink-0 order-2 space-y-4">
          {/* Study time pie chart – always visible */}
          <div className="rounded-xl border border-border bg-surface-elevated p-4 shadow-card">
            <h3 className="text-sm font-semibold text-ink mb-2">Time per course</h3>
            {studyTimeByCourse.length > 0 ? (
              <div className="flex items-center gap-4 group/pie">
                <div
                  className="w-20 h-20 rounded-full shrink-0 transition-transform duration-300 ease-out group-hover/pie:scale-110"
                  style={{
                    background: `conic-gradient(${studyTimeByCourse
                      .map((c, i) => {
                        const start = studyTimeByCourse.slice(0, i).reduce((s, x) => s + (x.mins / totalStudyMins) * 100, 0);
                        const end = start + (c.mins / totalStudyMins) * 100;
                        return `${PIE_COLORS[i % PIE_COLORS.length]} ${start}% ${end}%`;
                      })
                      .join(', ')})`,
                  }}
                  title={studyTimeByCourse.map(c => `${c.name}: ${Math.round(c.mins / 60 * 10) / 10}h`).join(', ')}
                />
                <div className="min-w-0 flex-1 space-y-1">
                  {studyTimeByCourse.slice(0, 5).map((c, i) => (
                    <div
                      key={c.name}
                      className="flex items-center gap-2 text-xs group/legend transition-colors duration-200 rounded px-1 -mx-1 hover:bg-surface-muted"
                      title={`${c.name}: ${Math.round(c.mins / 60 * 10) / 10} hours`}
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                      />
                      <span className="truncate text-ink">{c.name}</span>
                      <span className="text-ink-muted tabular-nums shrink-0">
                        {Math.round((c.mins / totalStudyMins) * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-ink-muted">
                Add courses from your syllabus, then click <strong>Generate Study Times</strong> above to see a breakdown of study time per course.
              </p>
            )}
          </div>

          <div className="rounded-xl border border-border bg-surface-elevated p-4 shadow-card">
            <h3 className="text-sm font-semibold text-ink mb-3">Sources</h3>
            {sources.length === 0 ? (
              <p className="text-xs text-ink-muted">
                No sources yet. Import a calendar to get started.
              </p>
            ) : (
              <ul className="space-y-2">
                {sources.map(src => (
                  <li
                    key={src.id}
                    className="flex items-center justify-between gap-2"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="relative shrink-0">
                        <button
                          type="button"
                          onClick={() =>
                            setColorEditId(c => (c === src.id ? null : src.id))
                          }
                          className="w-5 h-5 rounded-full border-2 border-white dark:border-gray-800 shadow-sm hover:ring-2 hover:ring-accent/50 transition-all cursor-pointer"
                          style={{
                            backgroundColor: src.color || '#64748B',
                          }}
                          title="Change color"
                        />
                        {colorEditId === src.id && (
                          <>
                            <div
                              className="fixed inset-0 z-40"
                              onClick={() => setColorEditId(null)}
                            />
                            <div className="absolute left-0 top-6 z-50 p-2 rounded-lg border border-border bg-surface shadow-lg min-w-[140px]">
                              <p className="text-[10px] font-medium text-ink-muted mb-1.5 uppercase tracking-wide">Color</p>
                              <div className="grid grid-cols-4 gap-1.5">
                                {SOURCE_COLOR_OPTIONS.map(({ hex, label }) => (
                                  <button
                                    key={hex}
                                    type="button"
                                    onClick={() => handleColorChange(src.id, hex)}
                                    className="w-7 h-7 rounded border border-border hover:scale-110 transition-transform"
                                    style={{ backgroundColor: hex }}
                                    title={label}
                                  />
                                ))}
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-ink truncate">
                          {src.source_label}
                        </p>
                        <p className="text-[10px] text-ink-muted font-mono tabular-nums">
                          {src.event_count} events ·{' '}
                          {src.source_type === 'google' ? 'Google' : 'ICS'}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button
                        onClick={() => handleSyncSource(src.id)}
                        disabled={syncingId === src.id}
                        title="Sync"
                        className="text-ink-muted hover:text-accent text-xs disabled:opacity-50 transition-colors"
                      >
                        ↻
                      </button>
                      <button
                        onClick={() => handleDeleteSource(src.id)}
                        title="Remove"
                        className="text-ink-muted hover:text-red-600 text-xs transition-colors"
                      >
                        ×
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <button
              onClick={handleConnectOrImport}
              className="mt-3 w-full text-xs font-medium text-accent hover:text-accent-hover transition-colors"
            >
              + Add Source
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
