import { useState, useRef, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import listPlugin from '@fullcalendar/list';
import './AppCalendar.css';

const DEFAULT_CATEGORY_COLORS = {
  class: '#3B82F6',
  office_hours: '#8B5CF6',
  exam: '#EF4444',
  assignment_deadline: '#F59E0B',
  meeting: '#6366F1',
  blocked_time: '#6B7280',
  personal: '#10B981',
  work: '#F97316',
  other: '#64748B',
};

export default function AppCalendar({
  calendarEvents = [],
  studyTimes = [],
  onEventClick,
  onDateSelect,
  onEventDrop,
  onEventResize,
}) {
  const calendarRef = useRef(null);
  const [currentView, setCurrentView] = useState('timeGridWeek');

  const transformEvents = useCallback(() => {
    const events = [];

    // Transform calendar events
    for (const evt of calendarEvents) {
      if (evt.sync_status !== 'active') continue;

      const title =
        evt.is_locally_modified && evt.local_title
          ? evt.local_title
          : evt.title;

      if (evt.event_kind === 'deadline_marker') {
        events.push({
          id: `cal-${evt.id}`,
          title: `\u{1F4CC} ${title}`,
          start: evt.start_date || evt.start_time,
          allDay: true,
          display: 'list-item',
          backgroundColor:
            DEFAULT_CATEGORY_COLORS[evt.event_category] || '#F59E0B',
          borderColor: '#EF4444',
          extendedProps: { type: 'calendar_event', data: evt },
          classNames: ['deadline-marker'],
        });
      } else if (evt.event_kind === 'all_day') {
        events.push({
          id: `cal-${evt.id}`,
          title,
          start: evt.start_date,
          end: evt.end_date,
          allDay: true,
          backgroundColor:
            evt.source_color ||
            DEFAULT_CATEGORY_COLORS[evt.event_category] ||
            '#64748B',
          extendedProps: { type: 'calendar_event', data: evt },
        });
      } else {
        const startTime =
          evt.is_locally_modified && evt.local_start_time
            ? evt.local_start_time
            : evt.start_time;
        const endTime =
          evt.is_locally_modified && evt.local_end_time
            ? evt.local_end_time
            : evt.end_time;
        events.push({
          id: `cal-${evt.id}`,
          title,
          start: startTime,
          end: endTime,
          backgroundColor:
            evt.source_color ||
            DEFAULT_CATEGORY_COLORS[evt.event_category] ||
            '#64748B',
          extendedProps: { type: 'calendar_event', data: evt },
        });
      }
    }

    // Transform study times (use course color when available)
    const STUDY_GREEN = '#10B981';
    const STUDY_LOCKED = '#059669';
    for (const st of studyTimes) {
      const baseColor = st.course_color || (st.is_locked ? STUDY_LOCKED : STUDY_GREEN);
      events.push({
        id: `study-${st.id}`,
        title: st.course_name
          ? `\u{1F4DA} ${st.course_name}`
          : '\u{1F4DA} Study',
        start: st.start_time,
        end: st.end_time,
        backgroundColor: baseColor,
        borderColor: baseColor,
        extendedProps: { type: 'study_time', data: st },
        classNames: st.is_locked ? ['locked-study'] : [],
        editable: !st.is_locked,
      });
    }

    return events;
  }, [calendarEvents, studyTimes]);

  const handleEventClick = info => {
    if (onEventClick) {
      onEventClick(info.event.extendedProps, info.jsEvent);
    }
  };

  const handleDateSelect = info => {
    if (onDateSelect) {
      onDateSelect({ start: info.start, end: info.end, allDay: info.allDay });
    }
  };

  const handleEventDrop = info => {
    if (onEventDrop) {
      onEventDrop({
        eventId: info.event.id,
        props: info.event.extendedProps,
        start: info.event.start,
        end: info.event.end,
      });
    }
  };

  const handleEventResize = info => {
    if (onEventResize) {
      onEventResize({
        eventId: info.event.id,
        props: info.event.extendedProps,
        start: info.event.start,
        end: info.event.end,
      });
    }
  };

  return (
    <div className="app-calendar-container app-calendar-google-style">
      <FullCalendar
        ref={calendarRef}
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
        initialView={currentView}
        locale="en-US"
        firstDay={0}
        dayHeaderContent={arg => (
          <div className="fc-day-header-content">
            <span className="fc-day-header-weekday">{arg.date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase()}</span>
            {currentView !== 'dayGridMonth' && (
              <span className="fc-day-header-day">{arg.date.getDate()}</span>
            )}
          </div>
        )}
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek',
        }}
        buttonText={{
          month: 'Month',
          week: 'Week',
          day: 'Day',
          list: 'List',
          listWeek: 'List',
        }}
        events={transformEvents()}
        editable={true}
        selectable={true}
        selectMirror={true}
        dayMaxEvents={true}
        weekends={true}
        slotMinTime="06:00:00"
        slotMaxTime="24:00:00"
        slotDuration="01:00:00"
        slotLabelInterval="01:00:00"
        snapDuration="00:15:00"
        allDaySlot={true}
        nowIndicator={true}
        eventClick={handleEventClick}
        select={handleDateSelect}
        eventDrop={handleEventDrop}
        eventResize={handleEventResize}
        viewDidMount={info => setCurrentView(info.view.type)}
        height={currentView === 'dayGridMonth' ? 'auto' : '70vh'}
        expandRows={currentView !== 'dayGridMonth'}
        stickyHeaderDates={true}
        eventTimeFormat={{
          hour: 'numeric',
          minute: '2-digit',
          meridiem: 'short',
        }}
      />
    </div>
  );
}
