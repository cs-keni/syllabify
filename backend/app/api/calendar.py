# Calendar API: Google Calendar import, ICS feed import, sync, events.
# OAuth flow for calendar scope; events.list; store in CalendarSources/CalendarEvents.
# See docs/GOOGLE-OAUTH.md.

import logging
import os
import re
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

from flask import Blueprint, Response, jsonify, redirect, request

from app.services.calendar_export_service import (
    build_ical_feed_for_user,
    get_or_create_feed_token,
    rotate_feed_token,
    set_feed_enabled,
)
from app.services.ics_parsing_service import (
    auto_detect_category,
    classify_event,
    fetch_ics_feed,
    hash_feed_url,
    parse_ics_content,
)

bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")
logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


def get_db():
    import mysql.connector
    port = os.getenv("DB_PORT", "3306")
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 3306
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=port,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=15,
    )


def _get_user_from_token():
    """Extract user_id from JWT. Returns (user_id, None) or (None, error_response)."""
    from app.api.auth import decode_token
    auth = request.headers.get("Authorization")
    payload = decode_token(auth)
    if not payload:
        return None, (jsonify({"error": "unauthorized"}), 401)
    try:
        user_id = int(payload.get("sub"))
        return user_id, None
    except (TypeError, ValueError):
        return None, (jsonify({"error": "unauthorized"}), 401)


def _get_google_credentials(user_id):
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


def _store_tokens(user_id, access_token, refresh_token, expires_at=None):
    """Upsert tokens in UserOAuthTokens."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO UserOAuthTokens (user_id, provider, access_token, refresh_token, expires_at)
               VALUES (%s, 'google', %s, %s, %s)
               ON DUPLICATE KEY UPDATE access_token = VALUES(access_token), refresh_token = VALUES(refresh_token),
               expires_at = VALUES(expires_at), updated_at = NOW()""",
            (user_id, access_token, refresh_token, expires_at),
        )
        conn.commit()
    finally:
        conn.close()


# In-memory state for OAuth (production: use Redis or signed cookie)
_oauth_state_store = {}


# ── OAuth Endpoints (unchanged) ────────────────────────────

@bp.route("/auth-url", methods=["GET"])
def auth_url():
    """Return Google OAuth URL for Calendar scope. Requires JWT."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        return jsonify({"error": "Google Calendar is not configured"}), 503

    state = secrets.token_urlsafe(32)
    _oauth_state_store[state] = {"user_id": user_id}

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": CALENDAR_SCOPE,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return jsonify({"url": url})


@bp.route("/callback", methods=["GET"])
def callback():
    """Handle OAuth redirect. Exchange code for tokens, store, redirect to frontend."""
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        return redirect(_frontend_redirect(f"/app/schedule?calendar_error={error}"))

    if not code or not state:
        return redirect(_frontend_redirect("/app/schedule?calendar_error=missing_params"))

    if state not in _oauth_state_store:
        return redirect(_frontend_redirect("/app/schedule?calendar_error=invalid_state"))

    user_id = _oauth_state_store.pop(state, {}).get("user_id")
    if not user_id:
        return redirect(_frontend_redirect("/app/schedule?calendar_error=invalid_state"))

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI],
                }
            },
            scopes=[CALENDAR_SCOPE],
            redirect_uri=GOOGLE_REDIRECT_URI,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        _store_tokens(
            user_id,
            creds.token,
            creds.refresh_token,
            creds.expiry,
        )
        return redirect(_frontend_redirect("/app/schedule?calendar_connected=1"))
    except Exception:
        return redirect(_frontend_redirect("/app/schedule?calendar_error=token_exchange_failed"))


def _frontend_redirect(path):
    """Build redirect URL to frontend."""
    base = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().split(",")[0].strip()
    return base.rstrip("/") + path


def _calendar_public_base_url():
    """Resolve public backend base URL used in export feed links."""
    configured = os.getenv("BACKEND_PUBLIC_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    return request.url_root.rstrip("/")


@bp.route("/list", methods=["GET"])
def list_calendars():
    """Return user's Google calendars. Requires Calendar OAuth."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    creds = _get_google_credentials(user_id)
    if not creds:
        return jsonify({"error": "calendar_not_connected", "message": "Connect Google Calendar first"}), 401

    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)
        result = service.calendarList().list().execute()
        items = result.get("items", [])
        calendars = [
            {
                "id": c.get("id"),
                "summary": c.get("summary", "Unnamed"),
                "primary": c.get("primary", False),
                "backgroundColor": c.get("backgroundColor") or None,
            }
            for c in items
        ]
        return jsonify({"calendars": calendars})
    except Exception as e:
        logger.warning("Calendar list failed: %s", e)
        return jsonify({"error": "calendar_api_failed", "message": str(e)}), 500


@bp.route("/status", methods=["GET"])
def status():
    """Return whether user has Calendar connected."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    creds = _get_google_credentials(user_id)
    connected = creds is not None
    return jsonify({"connected": connected})


# ── Calendar Sources ───────────────────────────────────────

@bp.route("/sources", methods=["GET"])
def get_sources():
    """Return user's calendar sources with event counts."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT cs.id, cs.source_type, cs.source_label, cs.feed_category,
                      cs.color, cs.is_active, cs.last_synced_at, cs.sync_error,
                      COUNT(ce.id) AS event_count
               FROM CalendarSources cs
               LEFT JOIN CalendarEvents ce ON ce.source_id = cs.id AND ce.sync_status = 'active'
               WHERE cs.user_id = %s
               GROUP BY cs.id
               ORDER BY cs.created_at""",
            (user_id,),
        )
        rows = cur.fetchall()
        sources = []
        for r in rows:
            sources.append({
                "id": r["id"],
                "source_type": r["source_type"],
                "source_label": r["source_label"],
                "feed_category": r["feed_category"],
                "color": r["color"],
                "is_active": bool(r["is_active"]),
                "last_synced_at": r["last_synced_at"].isoformat() if r.get("last_synced_at") else None,
                "sync_error": r["sync_error"],
                "event_count": r["event_count"],
            })
        return jsonify({"sources": sources})
    finally:
        conn.close()


@bp.route("/sources/<int:source_id>", methods=["PATCH"])
def patch_source(source_id):
    """Update a calendar source (e.g. color)."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    data = request.get_json() or {}
    color = data.get("color")

    if not color or not isinstance(color, str):
        return jsonify({"error": "color is required (hex string)"}), 400

    # Validate hex color
    if not re.match(r"^#[0-9A-Fa-f]{6}$", color):
        return jsonify({"error": "invalid color format (use #RRGGBB)"}), 400

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE CalendarSources SET color = %s WHERE id = %s AND user_id = %s",
            (color[:7], source_id, user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "source not found"}), 404
        return jsonify({"ok": True})
    finally:
        conn.close()


@bp.route("/sources/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    """Delete a calendar source (cascade deletes events)."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM CalendarSources WHERE id = %s AND user_id = %s",
            (source_id, user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "source not found"}), 404
        return jsonify({"ok": True})
    finally:
        conn.close()


# ── Google Calendar Import (refactored to use new tables) ──

@bp.route("/import", methods=["POST"])
def import_calendar():
    """Import events from selected Google calendars into CalendarSources/CalendarEvents."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    creds = _get_google_credentials(user_id)
    if not creds:
        return jsonify({"error": "calendar_not_connected", "message": "Connect Google Calendar first"}), 401

    data = request.get_json() or {}
    calendar_ids = data.get("calendar_ids") or []
    start_date = data.get("start_date") or ""
    end_date = data.get("end_date") or ""
    category = data.get("category", "other")

    if not calendar_ids:
        return jsonify({"error": "calendar_ids is required"}), 400

    # Use wide default range if no dates provided: 1 year past to 2 years future
    now = datetime.utcnow()
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return jsonify({"error": "invalid start_date or end_date"}), 400
    else:
        start_dt = now - timedelta(days=365)
        end_dt = now + timedelta(days=730)

    def to_rfc3339(dt):
        if dt.tzinfo is None:
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return dt.isoformat().replace("+00:00", "Z")

    time_min = to_rfc3339(start_dt)
    time_max = to_rfc3339(end_dt + timedelta(days=1))

    conn = get_db()
    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)

        # Fetch calendar list to get colors (Google Calendar API returns backgroundColor)
        cal_list = service.calendarList().list().execute()
        cal_entries = {c["id"]: c for c in cal_list.get("items", [])}

        total_imported = 0
        cur = conn.cursor(dictionary=True)

        for cal_id in calendar_ids[:20]:
            cal_entry = cal_entries.get(cal_id, {})
            cal_label = cal_entry.get("summary", cal_id[:100])
            cal_color = cal_entry.get("backgroundColor")
            if cal_color and not re.match(r"^#[0-9A-Fa-f]{6}$", cal_color):
                cal_color = None

            # Find or create CalendarSource for this Google calendar
            cur.execute(
                """SELECT id, feed_category FROM CalendarSources
                   WHERE user_id = %s AND source_type = 'google' AND google_calendar_id = %s""",
                (user_id, cal_id),
            )
            source_row = cur.fetchone()
            if source_row:
                source_id = source_row["id"]
                src_category = source_row.get("feed_category", "other")
                # Update color from Google if we have it and source was created without it
                if cal_color:
                    cur.execute(
                        "UPDATE CalendarSources SET color = %s, source_label = %s WHERE id = %s",
                        (cal_color, cal_label[:100], source_id),
                    )
            else:
                cur.execute(
                    """INSERT INTO CalendarSources
                       (user_id, source_type, source_label, google_calendar_id, feed_category, color)
                       VALUES (%s, 'google', %s, %s, %s, %s)""",
                    (user_id, cal_label[:100], cal_id, category, cal_color or "#3B82F6"),
                )
                source_id = cur.lastrowid
                src_category = category

            page_token = None
            events = []
            while True:
                events_result = (
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
                events.extend(events_result.get("items", []))
                page_token = events_result.get("nextPageToken")
                if not page_token:
                    break

            for ev in events:
                if ev.get("status") == "cancelled":
                    continue
                start = ev.get("start") or {}
                end = ev.get("end") or {}
                start_str = start.get("dateTime") or start.get("date")
                end_str = end.get("dateTime") or end.get("date")
                if not start_str or not end_str:
                    continue

                is_date_event = "date" in start and "dateTime" not in start
                ev_id = ev.get("id", "")
                title = (ev.get("summary") or "Untitled")[:500]
                description = (ev.get("description") or "")[:2000] or None
                location = (ev.get("location") or "")[:500] or None

                event_kind = classify_event(
                    is_date=is_date_event,
                    start_val=start_str,
                    end_val=end_str,
                    title=title,
                    source_category=src_category,
                )
                event_category = auto_detect_category(title, src_category)

                if is_date_event:
                    cur.execute(
                        """INSERT INTO CalendarEvents
                           (user_id, source_id, external_uid, instance_key, title, description, location,
                            start_date, end_date, event_kind, event_category, sync_status, original_data)
                           VALUES (%s, %s, %s, 'base', %s, %s, %s, %s, %s, %s, %s, 'active', %s)
                           ON DUPLICATE KEY UPDATE title = VALUES(title), start_date = VALUES(start_date),
                           end_date = VALUES(end_date), sync_status = 'active', description = VALUES(description)""",
                        (user_id, source_id, ev_id, title, description, location,
                         start_str, end_str, event_kind, event_category,
                         '{"source": "google"}'),
                    )
                else:
                    try:
                        ev_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        ev_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue

                    tz = start.get("timeZone", "")

                    cur.execute(
                        """INSERT INTO CalendarEvents
                           (user_id, source_id, external_uid, instance_key, title, description, location,
                            start_time, end_time, original_timezone, event_kind, event_category, sync_status, original_data)
                           VALUES (%s, %s, %s, 'base', %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s)
                           ON DUPLICATE KEY UPDATE title = VALUES(title), start_time = VALUES(start_time),
                           end_time = VALUES(end_time), sync_status = 'active', description = VALUES(description)""",
                        (user_id, source_id, ev_id, title, description, location,
                         ev_start, ev_end, tz or None, event_kind, event_category,
                         '{"source": "google"}'),
                    )
                total_imported += 1

            # Update source last_synced_at
            cur.execute(
                "UPDATE CalendarSources SET last_synced_at = NOW(), sync_error = NULL WHERE id = %s",
                (source_id,),
            )

        conn.commit()
        return jsonify({"ok": True, "imported_count": total_imported})
    except Exception as e:
        conn.rollback()
        logger.warning("Calendar import failed: %s", e)
        return jsonify({"error": "import_failed", "message": str(e)}), 500
    finally:
        conn.close()


# ── ICS Feed Import ────────────────────────────────────────

@bp.route("/import-ics", methods=["POST"])
def import_ics():
    """Import events from an ICS/iCal feed URL."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    label = (data.get("label") or "").strip()
    category = data.get("category", "other")

    if not url:
        return jsonify({"error": "url is required"}), 400
    if not label:
        return jsonify({"error": "label is required"}), 400

    url_hash = hash_feed_url(url)

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)

        # Check for duplicate
        cur.execute(
            "SELECT id FROM CalendarSources WHERE user_id = %s AND feed_url_hash = %s",
            (user_id, url_hash),
        )
        if cur.fetchone():
            return jsonify({"error": "This feed URL is already imported"}), 409

        # Fetch and parse (expand recurring events over a reasonable horizon)
        ics_text = fetch_ics_feed(url)
        now = datetime.utcnow()
        expand_start = (now - timedelta(days=365)).isoformat()
        expand_end = (now + timedelta(days=365)).isoformat()
        events = parse_ics_content(
            ics_text,
            expand_start=expand_start,
            expand_end=expand_end,
            source_category=category,
        )

        # Create source
        cur.execute(
            """INSERT INTO CalendarSources
               (user_id, source_type, source_label, feed_url, feed_url_hash, feed_category)
               VALUES (%s, 'ics_url', %s, %s, %s, %s)""",
            (user_id, label[:100], url, url_hash, category),
        )
        source_id = cur.lastrowid

        # Bulk insert events
        imported = _insert_events(cur, user_id, source_id, events)

        cur.execute(
            "UPDATE CalendarSources SET last_synced_at = NOW(), sync_error = NULL WHERE id = %s",
            (source_id,),
        )
        conn.commit()
        return jsonify({"ok": True, "source_id": source_id, "imported_count": imported})
    except Exception as e:
        conn.rollback()
        logger.warning("ICS import failed: %s", e)
        return jsonify({"error": "import_failed", "message": str(e)}), 500
    finally:
        conn.close()


# ── Sync Source ────────────────────────────────────────────

@bp.route("/sync-source/<int:source_id>", methods=["POST"])
def sync_source(source_id):
    """Re-sync a calendar source (ICS or Google)."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM CalendarSources WHERE id = %s AND user_id = %s",
            (source_id, user_id),
        )
        source = cur.fetchone()
        if not source:
            return jsonify({"error": "source not found"}), 404

        if source["source_type"] == "ics_url":
            return _sync_ics_source(conn, cur, user_id, source)
        elif source["source_type"] == "google":
            return _sync_google_source(conn, cur, user_id, source)
        else:
            return jsonify({"error": "unsupported source type"}), 400
    except Exception as e:
        conn.rollback()
        logger.warning("Sync failed for source %s: %s", source_id, e)
        return jsonify({"error": "sync_failed", "message": str(e)}), 500
    finally:
        conn.close()


def _sync_ics_source(conn, cur, user_id, source):
    """Re-fetch and re-parse an ICS feed."""
    ics_text = fetch_ics_feed(source["feed_url"])
    now = datetime.utcnow()
    events = parse_ics_content(
        ics_text,
        expand_start=(now - timedelta(days=365)).isoformat(),
        expand_end=(now + timedelta(days=365)).isoformat(),
        source_category=source["feed_category"],
    )

    # Mark existing events as stale
    cur.execute(
        "UPDATE CalendarEvents SET sync_status = 'stale' WHERE source_id = %s",
        (source["id"],),
    )

    # Upsert fresh events
    synced = _insert_events(cur, user_id, source["id"], events)

    # Mark remaining stale events as deleted_at_source
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


def _sync_google_source(conn, cur, user_id, source):
    """Re-fetch events from Google Calendar API."""
    creds = _get_google_credentials(user_id)
    if not creds:
        return jsonify({"error": "calendar_not_connected"}), 401

    from googleapiclient.discovery import build
    service = build("calendar", "v3", credentials=creds)

    cal_id = source["google_calendar_id"]

    # Fetch calendar list to update color from Google
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
        pass  # Non-fatal; continue with event sync
    # Use wide date range so scheduler sees full term (1 year past, 1 year future)
    now = datetime.utcnow()
    time_min = (now - timedelta(days=365)).isoformat() + "Z"
    time_max = (now + timedelta(days=365)).isoformat() + "Z"

    page_token = None
    all_events = []
    while True:
        events_result = (
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
        all_events.extend(events_result.get("items", []))
        page_token = events_result.get("nextPageToken")
        if not page_token:
            break

    # Mark existing as stale
    cur.execute(
        "UPDATE CalendarEvents SET sync_status = 'stale' WHERE source_id = %s",
        (source["id"],),
    )

    synced = 0
    for ev in all_events:
        if ev.get("status") == "cancelled":
            continue
        start = ev.get("start") or {}
        end = ev.get("end") or {}
        start_str = start.get("dateTime") or start.get("date")
        end_str = end.get("dateTime") or end.get("date")
        if not start_str or not end_str:
            continue

        is_date_event = "date" in start and "dateTime" not in start
        ev_id = ev.get("id", "")
        title = (ev.get("summary") or "Untitled")[:500]
        description = (ev.get("description") or "")[:2000] or None
        location = (ev.get("location") or "")[:500] or None
        src_category = source.get("feed_category", "other")
        event_kind = classify_event(is_date_event, start_str, end_str, title, src_category)
        event_category = auto_detect_category(title, src_category)

        if is_date_event:
            cur.execute(
                """INSERT INTO CalendarEvents
                   (user_id, source_id, external_uid, instance_key, title, description, location,
                    start_date, end_date, event_kind, event_category, sync_status)
                   VALUES (%s, %s, %s, 'base', %s, %s, %s, %s, %s, %s, %s, 'active')
                   ON DUPLICATE KEY UPDATE title = VALUES(title), start_date = VALUES(start_date),
                   end_date = VALUES(end_date), sync_status = 'active'""",
                (user_id, source["id"], ev_id, title, description, location,
                 start_str, end_str, event_kind, event_category),
            )
        else:
            try:
                ev_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                ev_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            tz = start.get("timeZone", "")
            cur.execute(
                """INSERT INTO CalendarEvents
                   (user_id, source_id, external_uid, instance_key, title, description, location,
                    start_time, end_time, original_timezone, event_kind, event_category, sync_status)
                   VALUES (%s, %s, %s, 'base', %s, %s, %s, %s, %s, %s, %s, %s, 'active')
                   ON DUPLICATE KEY UPDATE title = VALUES(title), start_time = VALUES(start_time),
                   end_time = VALUES(end_time), sync_status = 'active'""",
                (user_id, source["id"], ev_id, title, description, location,
                 ev_start, ev_end, tz or None, event_kind, event_category),
            )
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


# ── Events Endpoint (refactored) ──────────────────────────

@bp.route("/events", methods=["GET"])
def get_events():
    """Return CalendarEvents for current user with optional filters."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    source_id = request.args.get("source_id", type=int)
    event_kind = request.args.get("event_kind", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        query = """SELECT ce.*, cs.source_label, cs.color AS source_color, cs.source_type
                   FROM CalendarEvents ce
                   JOIN CalendarSources cs ON cs.id = ce.source_id
                   WHERE ce.user_id = %s AND ce.sync_status = 'active'"""
        params = [user_id]

        if source_id:
            query += " AND ce.source_id = %s"
            params.append(source_id)
        if event_kind:
            query += " AND ce.event_kind = %s"
            params.append(event_kind)
        if start_date:
            query += " AND (ce.start_time >= %s OR ce.start_date >= %s)"
            params.extend([start_date, start_date])
        if end_date:
            query += " AND (ce.end_time <= %s OR ce.end_date <= %s)"
            params.extend([end_date, end_date])

        query += " ORDER BY COALESCE(ce.start_time, ce.start_date)"
        cur.execute(query, params)
        rows = cur.fetchall()

        events = []
        for r in rows:
            events.append({
                "id": r["id"],
                "source_id": r["source_id"],
                "source_label": r["source_label"],
                "source_color": r["source_color"],
                "source_type": r["source_type"],
                "external_uid": r["external_uid"],
                "title": r["title"],
                "description": r["description"],
                "location": r["location"],
                "start_time": r["start_time"].isoformat() if r.get("start_time") else None,
                "end_time": r["end_time"].isoformat() if r.get("end_time") else None,
                "original_timezone": r["original_timezone"],
                "start_date": r["start_date"].isoformat() if r.get("start_date") else None,
                "end_date": r["end_date"].isoformat() if r.get("end_date") else None,
                "event_kind": r["event_kind"],
                "event_category": r["event_category"],
                "sync_status": r["sync_status"],
                "is_recurring_instance": bool(r.get("is_recurring_instance")),
                "is_locally_modified": bool(r.get("is_locally_modified")),
                "local_title": r.get("local_title"),
                "local_start_time": r["local_start_time"].isoformat() if r.get("local_start_time") else None,
                "local_end_time": r["local_end_time"].isoformat() if r.get("local_end_time") else None,
                "local_notes": r.get("local_notes"),
            })
        return jsonify({"events": events})
    finally:
        conn.close()


@bp.route("/export/<string:feed_token>.ics", methods=["GET"])
def export_study_times_ics(feed_token):
    """Public iCal subscription endpoint. Auth intentionally not required."""
    token = (feed_token or "").strip()
    if not token:
        return jsonify({"error": "not found"}), 404

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT id FROM Users
               WHERE ical_feed_token = %s
                 AND COALESCE(ical_feed_enabled, 1) = 1
               LIMIT 1""",
            (token,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return jsonify({"error": "not found"}), 404

        ical_bytes = build_ical_feed_for_user(conn, int(row["id"]))
        return Response(
            ical_bytes,
            status=200,
            headers={
                "Content-Type": "text/calendar; charset=utf-8",
                "Content-Disposition": 'inline; filename=\"syllabify-study-plan.ics\"',
                "Cache-Control": "private, max-age=300",
            },
        )
    finally:
        conn.close()


@bp.route("/export/token", methods=["GET"])
def get_export_feed_token():
    """Get (or create) current user's personal iCal feed URL."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    conn = get_db()
    try:
        token, enabled = get_or_create_feed_token(conn, user_id)
        feed_url = f"{_calendar_public_base_url()}/api/calendar/export/{token}.ics"
        return jsonify({"feedUrl": feed_url, "enabled": bool(enabled)})
    finally:
        conn.close()


@bp.route("/export/token/rotate", methods=["POST"])
def rotate_export_feed_token():
    """Rotate current user's feed token. Old URL becomes invalid."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    conn = get_db()
    try:
        token = rotate_feed_token(conn, user_id)
        feed_url = f"{_calendar_public_base_url()}/api/calendar/export/{token}.ics"
        return jsonify({"feedUrl": feed_url, "ok": True})
    finally:
        conn.close()


@bp.route("/export/token", methods=["PATCH"])
def patch_export_feed_status():
    """Enable/disable current user's feed token."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    body = request.get_json(silent=True) or {}
    if "enabled" not in body:
        return jsonify({"error": "enabled is required"}), 400

    conn = get_db()
    try:
        set_feed_enabled(conn, user_id, bool(body.get("enabled")))
        token, enabled = get_or_create_feed_token(conn, user_id)
        feed_url = f"{_calendar_public_base_url()}/api/calendar/export/{token}.ics"
        return jsonify({"feedUrl": feed_url, "enabled": bool(enabled), "ok": True})
    finally:
        conn.close()


# ── Legacy sync endpoint (kept for backward compat) ───────

@bp.route("/sync", methods=["POST"])
def sync_calendar():
    """Re-fetch events from all connected Google calendar sources."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id FROM CalendarSources WHERE user_id = %s AND source_type = 'google'",
            (user_id,),
        )
        sources = cur.fetchall()
    finally:
        conn.close()

    if not sources:
        return jsonify({"error": "no_calendars_connected", "message": "Import calendars first"}), 400

    total_synced = 0
    for src in sources:
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM CalendarSources WHERE id = %s", (src["id"],))
            source = cur.fetchone()
            if source:
                resp = _sync_google_source(conn, cur, user_id, source)
                resp_data = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
                total_synced += resp_data.get("synced_count", 0)
        except Exception as e:
            logger.warning("Sync failed for source %s: %s", src["id"], e)
        finally:
            conn.close()

    return jsonify({"ok": True, "synced_count": total_synced})


# ── Helpers ────────────────────────────────────────────────

def _insert_events(cur, user_id, source_id, events):
    """Bulk insert/upsert parsed events into CalendarEvents. Returns count."""
    import json
    count = 0
    for ev in events:
        original_data_str = json.dumps(ev.get("original_data") or {})
        if ev.get("event_kind") in ("all_day", "deadline_marker"):
            cur.execute(
                """INSERT INTO CalendarEvents
                   (user_id, source_id, external_uid, instance_key, recurrence_id,
                    title, description, location, start_date, end_date,
                    event_kind, event_category, sync_status, recurrence_rule,
                    is_recurring_instance, original_data)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s)
                   ON DUPLICATE KEY UPDATE title = VALUES(title), start_date = VALUES(start_date),
                   end_date = VALUES(end_date), sync_status = 'active', description = VALUES(description)""",
                (user_id, source_id, ev["external_uid"], ev.get("instance_key", "base"),
                 ev.get("recurrence_id"), ev["title"], ev.get("description"),
                 ev.get("location"), ev.get("start_date"), ev.get("end_date"),
                 ev["event_kind"], ev["event_category"], ev.get("recurrence_rule"),
                 ev.get("is_recurring_instance", False), original_data_str),
            )
        else:
            cur.execute(
                """INSERT INTO CalendarEvents
                   (user_id, source_id, external_uid, instance_key, recurrence_id,
                    title, description, location, start_time, end_time, original_timezone,
                    event_kind, event_category, sync_status, recurrence_rule,
                    is_recurring_instance, original_data)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s)
                   ON DUPLICATE KEY UPDATE title = VALUES(title), start_time = VALUES(start_time),
                   end_time = VALUES(end_time), sync_status = 'active', description = VALUES(description)""",
                (user_id, source_id, ev["external_uid"], ev.get("instance_key", "base"),
                 ev.get("recurrence_id"), ev["title"], ev.get("description"),
                 ev.get("location"), ev.get("start_time"), ev.get("end_time"),
                 ev.get("original_timezone"), ev["event_kind"], ev["event_category"],
                 ev.get("recurrence_rule"), ev.get("is_recurring_instance", False),
                 original_data_str),
            )
        count += 1
    return count
