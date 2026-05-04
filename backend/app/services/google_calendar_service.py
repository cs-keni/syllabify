"""Google Calendar OAuth + API helpers, extracted from api/calendar.py."""

import logging
import os
import re
from datetime import datetime, timedelta

from app.db.connection import get_db
from app.services.ics_parsing_service import auto_detect_category, classify_event

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


def get_google_credentials(user_id):
    """Load credentials from UserOAuthTokens. Refresh if expired. Returns credentials or None."""
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT access_token, refresh_token, expires_at FROM UserOAuthTokens
               WHERE user_id = %s AND provider = 'google'""",
            (user_id,),
        )
        row = cur.fetchone()
        if not row or not row.get("refresh_token"):
            return None

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=row.get("access_token"),
            refresh_token=row.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            expires_at = datetime.utcnow() + timedelta(seconds=3600) if creds.expiry else None
            cur.execute(
                """UPDATE UserOAuthTokens SET access_token = %s, expires_at = %s, updated_at = NOW()
                   WHERE user_id = %s AND provider = 'google'""",
                (creds.token, expires_at, user_id),
            )
            conn.commit()

        return creds
    except Exception:
        return None
    finally:
        conn.close()


def store_google_tokens(user_id, access_token, refresh_token, expires_at=None):
    """Upsert Google OAuth tokens in UserOAuthTokens."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO UserOAuthTokens (user_id, provider, access_token, refresh_token, expires_at)
               VALUES (%s, 'google', %s, %s, %s)
               ON CONFLICT (user_id, provider) DO UPDATE SET
               access_token = EXCLUDED.access_token, refresh_token = EXCLUDED.refresh_token,
               expires_at = EXCLUDED.expires_at, updated_at = NOW()""",
            (user_id, access_token, refresh_token, expires_at),
        )
        conn.commit()
    finally:
        conn.close()


def build_google_service(credentials):
    """Build a Google Calendar API service object."""
    from googleapiclient.discovery import build
    return build("calendar", "v3", credentials=credentials)


def fetch_events_paginated(service, cal_id, time_min, time_max):
    """Fetch all events from a Google Calendar, handling pagination. Returns list of event dicts."""
    page_token = None
    all_events = []
    while True:
        result = (
            service.events()
            .list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
                maxResults=500,
            )
            .execute()
        )
        all_events.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return all_events


def parse_google_event(ev, src_category):
    """
    Parse a raw Google Calendar event dict into a normalized dict.
    Returns None if the event should be skipped.
    """
    if ev.get("status") == "cancelled":
        return None

    start = ev.get("start") or {}
    end = ev.get("end") or {}
    start_str = start.get("dateTime") or start.get("date")
    end_str = end.get("dateTime") or end.get("date")
    if not start_str or not end_str:
        return None

    is_date_event = "date" in start and "dateTime" not in start
    title = (ev.get("summary") or "Untitled")[:500]
    description = (ev.get("description") or "")[:2000] or None
    location = (ev.get("location") or "")[:500] or None
    tz = start.get("timeZone", "") or None
    ev_id = ev.get("id", "")

    event_kind = classify_event(is_date_event, start_str, end_str, title, src_category)
    event_category = auto_detect_category(title, src_category)

    parsed = {
        "external_uid": ev_id,
        "title": title,
        "description": description,
        "location": location,
        "event_kind": event_kind,
        "event_category": event_category,
        "is_date_event": is_date_event,
        "start_str": start_str,
        "end_str": end_str,
        "timezone": tz,
    }

    if not is_date_event:
        try:
            parsed["start_dt"] = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            parsed["end_dt"] = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    return parsed


def upsert_google_event(cur, user_id, source_id, parsed_ev):
    """Upsert a single parsed Google event into CalendarEvents. Returns True if inserted/updated."""
    if parsed_ev["is_date_event"]:
        cur.execute(
            """INSERT INTO CalendarEvents
               (user_id, source_id, external_uid, instance_key, title, description, location,
                start_date, end_date, event_kind, event_category, sync_status)
               VALUES (%s, %s, %s, 'base', %s, %s, %s, %s, %s, %s, %s, 'active')
               ON CONFLICT (source_id, external_uid, instance_key) DO UPDATE SET
               title = EXCLUDED.title, start_date = EXCLUDED.start_date,
               end_date = EXCLUDED.end_date, sync_status = 'active',
               description = EXCLUDED.description""",
            (
                user_id, source_id, parsed_ev["external_uid"],
                parsed_ev["title"], parsed_ev["description"], parsed_ev["location"],
                parsed_ev["start_str"], parsed_ev["end_str"],
                parsed_ev["event_kind"], parsed_ev["event_category"],
            ),
        )
    else:
        cur.execute(
            """INSERT INTO CalendarEvents
               (user_id, source_id, external_uid, instance_key, title, description, location,
                start_time, end_time, original_timezone, event_kind, event_category, sync_status)
               VALUES (%s, %s, %s, 'base', %s, %s, %s, %s, %s, %s, %s, %s, 'active')
               ON CONFLICT (source_id, external_uid, instance_key) DO UPDATE SET
               title = EXCLUDED.title, start_time = EXCLUDED.start_time,
               end_time = EXCLUDED.end_time, sync_status = 'active',
               description = EXCLUDED.description""",
            (
                user_id, source_id, parsed_ev["external_uid"],
                parsed_ev["title"], parsed_ev["description"], parsed_ev["location"],
                parsed_ev["start_dt"], parsed_ev["end_dt"], parsed_ev["timezone"],
                parsed_ev["event_kind"], parsed_ev["event_category"],
            ),
        )
    return True


def sync_google_source(conn, cur, user_id, source):
    """
    Re-fetch events from Google Calendar API for a single source.
    Marks old events stale, upserts fresh ones, returns (synced_count, error_or_None).
    """
    from flask import jsonify

    creds = get_google_credentials(user_id)
    if not creds:
        return jsonify({"error": "calendar_not_connected"}), 401

    service = build_google_service(creds)
    cal_id = source["google_calendar_id"]

    # Try to refresh color/label from Google (non-fatal)
    try:
        cal_list = service.calendarList().list().execute()
        for c in cal_list.get("items", []):
            if c.get("id") == cal_id:
                cal_color = c.get("backgroundColor")
                cal_label = c.get("summary", source.get("source_label", ""))[:100]
                if cal_color and re.match(r"^#[0-9A-Fa-f]{6}$", cal_color):
                    cur.execute(
                        "UPDATE CalendarSources SET color = %s, source_label = %s WHERE id = %s",
                        (cal_color, cal_label, source["id"]),
                    )
                break
    except Exception:
        pass

    now = datetime.utcnow()
    time_min = (now - timedelta(days=365)).isoformat() + "Z"
    time_max = (now + timedelta(days=365)).isoformat() + "Z"

    all_events = fetch_events_paginated(service, cal_id, time_min, time_max)

    cur.execute(
        "UPDATE CalendarEvents SET sync_status = 'stale' WHERE source_id = %s",
        (source["id"],),
    )

    synced = 0
    src_category = source.get("feed_category", "other")
    for ev in all_events:
        parsed = parse_google_event(ev, src_category)
        if parsed is None:
            continue
        upsert_google_event(cur, user_id, source["id"], parsed)
        synced += 1

    cur.execute(
        "UPDATE CalendarEvents SET sync_status = 'deleted_at_source' WHERE source_id = %s AND sync_status = 'stale'",
        (source["id"],),
    )
    cur.execute(
        "UPDATE CalendarSources SET last_synced_at = NOW(), sync_error = NULL WHERE id = %s",
        (source["id"],),
    )
    conn.commit()
    return jsonify({"ok": True, "synced_count": synced})
