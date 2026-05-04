/**
 * Schedule page. Displays calendar via AppCalendar (FullCalendar).
 * Supports Google Calendar and ICS feed import, sources sidebar.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../api/client';
import AppCalendar from '../components/AppCalendar';
import UnifiedImportModal from '../components/UnifiedImportModal';
import ScheduleToolbar from '../components/schedule/ScheduleToolbar';
import ScheduleSidebar from '../components/schedule/ScheduleSidebar';
import GenerateModal from '../components/schedule/GenerateModal';
import ExportModal from '../components/schedule/ExportModal';
import StudyBlockPopover from '../components/schedule/StudyBlockPopover';

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
  const [showProposedScheduleModal, setShowProposedScheduleModal] =
    useState(false);
  const [proposedSlots, setProposedSlots] = useState([]);
  const [applyingSchedule, setApplyingSchedule] = useState(false);
  const [clearingSchedule, setClearingSchedule] = useState(false);

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
  const shortcutHandlersRef = useRef({});
  const [viewWindow, setViewWindow] = useState(null); // { start: Date, end: Date }

  // Keyboard shortcuts: G = generate, E = export (schedule-page-specific)
  useEffect(() => {
    const onKey = e => {
      const inInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(
        document.activeElement?.tagName
      );
      if (inInput || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === 'G') shortcutHandlersRef.current.generate?.();
      if (e.key === 'E') shortcutHandlersRef.current.export?.();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

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
        const startDate = viewWindow
          ? viewWindow.start.toISOString().slice(0, 10)
          : null;
        const endDate = viewWindow
          ? viewWindow.end.toISOString().slice(0, 10)
          : null;
        const stData = await api.getStudyTimes(
          token,
          activeTerm.id,
          startDate,
          endDate
        );
        setStudyTimes(stData.study_times || []);
      } catch (err) {
        console.warn('Failed to fetch study times:', err?.message);
      }
    }
  }, [token, activeTerm, viewWindow]);

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
      (async () => {
        for (const src of staleSources) {
          try {
            await api.syncSource(token, src.id);
          } catch {
            /* ignore stale sync errors */
          }
        }
        fetchData();
      })();
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

  // Keep shortcut handlers up to date every render (avoids stale closure in keydown listener)
  shortcutHandlersRef.current = {
    generate: () => !generating && handleGenerateStudyTimes(),
    export: () => !showExportModal && handleOpenExportModal(),
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
      toast(
        t => (
          <span className="flex items-center gap-2 text-sm">
            Block pinned.
            <button
              className="font-semibold text-accent underline"
              onClick={() => {
                toast.dismiss(t.id);
                shortcutHandlersRef.current.generate?.();
              }}
            >
              Re-optimize remaining?
            </button>
          </span>
        ),
        { duration: 6000 }
      );
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
      toast('All blocks on this day are already locked.');
      return;
    }
    try {
      await Promise.all(
        blocksOnDay.map(st =>
          api.updateStudyTime(token, st.id, { is_locked: true })
        )
      );
      setStudyTimes(prev =>
        prev.map(st =>
          blocksOnDay.some(b => b.id === st.id)
            ? { ...st, is_locked: true }
            : st
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
      const data = await api.generateStudyTimes(token, termToUse.id, {
        preview: true,
      });
      const slots = data.study_times || [];
      const count = data.created_count ?? slots.length;
      if (count === 0) {
        toast(
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
      const data = await api.generateStudyTimes(token, activeTerm.id, {
        preview: false,
      });
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

  const handleClearStudyTimes = async () => {
    if (!token || !activeTerm?.id) return;
    setClearingSchedule(true);
    try {
      const data = await api.clearStudyTimes(token, activeTerm.id);
      const count = data.deleted_count ?? 0;
      toast.success(
        count > 0
          ? `Cleared ${count} study block(s).`
          : 'No study blocks to clear.'
      );
      fetchData();
    } catch (err) {
      toast.error(err.message || 'Failed to clear study times');
    } finally {
      setClearingSchedule(false);
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

  // Shared palette for courses without explicit color (must match backend/AppCalendar)
  const COURSE_COLORS = [
    '#3B82F6',
    '#10B981',
    '#F59E0B',
    '#EF4444',
    '#8B5CF6',
    '#EC4899',
    '#06B6D4',
    '#64748B',
  ];
  const courseColor = (courseId, dbColor) =>
    dbColor || COURSE_COLORS[(courseId ?? 0) % COURSE_COLORS.length];

  // Pie chart data: study time per course (minutes), with color synced to calendar
  const studyTimeByCourse = (() => {
    const byCourse = {};
    for (const st of studyTimes) {
      const name = st.course_name || 'Study';
      const start = new Date(st.start_time).getTime();
      const end = new Date(st.end_time).getTime();
      const mins = Math.round((end - start) / 60000);
      const color = courseColor(st.course_id, st.course_color);
      if (!byCourse[name]) {
        byCourse[name] = { mins: 0, course_id: st.course_id, color };
      }
      byCourse[name].mins += mins;
    }
    return Object.entries(byCourse)
      .map(([name, data]) => ({ name, mins: data.mins, color: data.color }))
      .sort((a, b) => b.mins - a.mins);
  })();

  const totalStudyMins = studyTimeByCourse.reduce((s, x) => s + x.mins, 0);

  // Weekly study hours — grouped by ISO Monday of each week
  const weeklyHours = useMemo(() => {
    const byWeek = {};
    for (const st of studyTimes) {
      const d = new Date(st.start_time);
      const monday = new Date(d);
      monday.setHours(0, 0, 0, 0);
      monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
      const key = monday.toISOString().slice(0, 10);
      const mins = (new Date(st.end_time) - new Date(st.start_time)) / 60000;
      byWeek[key] = (byWeek[key] || 0) + mins;
    }
    return Object.entries(byWeek)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([week, mins]) => ({
        week,
        hours: Math.round((mins / 60) * 10) / 10,
        isPast: new Date(week) < new Date(new Date().setHours(0, 0, 0, 0)),
      }));
  }, [studyTimes]);

  // Merge consecutive same-course blocks for display (e.g. 7:00–7:15 + 7:15–8:15 → 7:00–8:15)
  const mergedStudyTimes = useMemo(() => {
    if (!studyTimes?.length) return [];
    const sorted = [...studyTimes].sort(
      (a, b) => new Date(a.start_time) - new Date(b.start_time)
    );
    const merged = [];
    for (const st of sorted) {
      const last = merged[merged.length - 1];
      const sameCourse = last && last.course_id === st.course_id;
      const adjacent =
        last &&
        new Date(last.end_time).getTime() === new Date(st.start_time).getTime();
      if (sameCourse && adjacent) {
        last.end_time = st.end_time;
        last.id = last.id; // keep first block's id for edit/delete
      } else {
        merged.push({ ...st });
      }
    }
    return merged;
  }, [studyTimes]);

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
      <ScheduleToolbar
        generating={generating}
        clearingSchedule={clearingSchedule}
        calendarConnected={calendarConnected}
        studyTimesCount={studyTimes.length}
        token={token}
        onGenerate={handleGenerateStudyTimes}
        onClear={handleClearStudyTimes}
        onConnectOrImport={handleConnectOrImport}
        onExport={handleOpenExportModal}
      />

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
        <GenerateModal
          proposedSlots={proposedSlots}
          applyingSchedule={applyingSchedule}
          onApply={handleApplyProposedSchedule}
          onClose={() => setShowProposedScheduleModal(false)}
        />
      )}

      {showExportModal && (
        <ExportModal
          loading={exportLoading}
          feedUrl={exportFeedUrl}
          enabled={exportEnabled}
          error={exportError}
          onCopy={handleCopyExportUrl}
          onClose={() => setShowExportModal(false)}
        />
      )}

      {studyTimes.length === 0 && calendarEvents.length === 0 && (
        <div className="rounded-xl border border-dashed border-border bg-surface-elevated/50 p-6 text-center animate-fade-in">
          <p className="text-sm font-medium text-ink mb-1">
            No study blocks yet
          </p>
          <p className="text-xs text-ink-muted mb-3">
            Upload a syllabus to generate a balanced study schedule
            automatically.
          </p>
          <Link
            to="/app"
            className="inline-block rounded-button bg-primary px-4 py-2 text-sm font-medium text-primary-inv hover:opacity-90 transition-opacity no-underline"
          >
            Go to Dashboard
          </Link>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main calendar */}
        <div className="flex-1 min-w-0 order-1">
          <AppCalendar
            calendarEvents={calendarEvents}
            studyTimes={mergedStudyTimes}
            onEventDrop={handleStudyTimeMove}
            onEventResize={handleStudyTimeMove}
            onEventClick={handleEventClickAll}
            onEventHover={handleEventHover}
            onEventHoverEnd={handleEventHoverEnd}
            onDatesSet={({ start, end }) => setViewWindow({ start, end })}
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
                  {hoverPreview.data.assignment_name && (
                    <p className="text-xs text-ink-muted mt-0.5 truncate">
                      {hoverPreview.data.assignment_name}
                    </p>
                  )}
                  <p className="text-xs text-ink-muted mt-0.5">
                    {hoverPreview.data.is_locked
                      ? 'Locked (kept when regenerating)'
                      : 'Unlocked (replaced when regenerating)'}{' '}
                    · Click to edit
                  </p>
                  {hoverPreview.data.start_time && (
                    <p className="text-xs text-ink-muted font-mono mt-1">
                      {new Date(
                        hoverPreview.data.start_time
                      ).toLocaleTimeString([], {
                        hour: 'numeric',
                        minute: '2-digit',
                      })}{' '}
                      –{' '}
                      {new Date(hoverPreview.data.end_time).toLocaleTimeString(
                        [],
                        { hour: 'numeric', minute: '2-digit' }
                      )}
                    </p>
                  )}
                </>
              ) : (
                <>
                  <p className="font-medium text-ink truncate">
                    {hoverPreview.data.title}
                  </p>
                  {(hoverPreview.data.start_time ||
                    hoverPreview.data.start_date) && (
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
                  <p className="text-[10px] text-ink-subtle mt-1.5">
                    Click to edit
                  </p>
                </>
              )}
            </div>
          )}
          <StudyBlockPopover
            popover={popover}
            onToggleLock={handleToggleLock}
            onLockDay={handleLockEntireDay}
            onClose={() => setPopover(null)}
          />
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
                    <p className="text-[10px] font-medium text-ink-muted mb-1.5 uppercase tracking-wide">
                      Event color
                    </p>
                    <p className="text-[10px] text-ink-muted mb-1.5">
                      Changes all events from this source (e.g. this Google
                      calendar).
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {SOURCE_COLOR_OPTIONS.map(({ hex, label }) => (
                        <button
                          key={hex}
                          type="button"
                          onClick={() => {
                            const src = sources.find(
                              s => s.id === eventDetail.event.source_id
                            );
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

        <ScheduleSidebar
          studyTimeByCourse={studyTimeByCourse}
          totalStudyMins={totalStudyMins}
          weeklyHours={weeklyHours}
          sources={sources}
          syncingId={syncingId}
          colorEditId={colorEditId}
          onColorEditToggle={id => setColorEditId(c => (c === id ? null : id))}
          onColorChange={handleColorChange}
          onSyncSource={handleSyncSource}
          onDeleteSource={handleDeleteSource}
          onAddSource={handleConnectOrImport}
        />
      </div>
    </div>
  );
}
