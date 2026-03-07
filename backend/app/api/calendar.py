# Calendar API: Google Calendar import, sync, events.
# OAuth flow for calendar scope; events.list; store in ExternalEvents.
# See docs/GOOGLE-OAUTH.md.

import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

from flask import Blueprint, jsonify, redirect, request

bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")

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
            }
            for c in items
        ]
        return jsonify({"calendars": calendars})
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Calendar list failed: %s", e)
        return jsonify({"error": "calendar_api_failed", "message": str(e)}), 500


@bp.route("/import", methods=["POST"])
def import_calendar():
    """Import events from selected calendars. Body: { calendar_ids: [], start_date, end_date }."""
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

    if not calendar_ids:
        return jsonify({"error": "calendar_ids is required"}), 400

    try:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else None
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else None
    except (ValueError, TypeError):
        return jsonify({"error": "invalid start_date or end_date"}), 400

    if not start_dt or not end_dt:
        return jsonify({"error": "start_date and end_date are required"}), 400

    conn = get_db()
    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)
        time_min = start_dt.isoformat()
        time_max = end_dt.isoformat()

        total_imported = 0
        cur = conn.cursor(dictionary=True)

        for cal_id in calendar_ids[:20]:
            events_result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            for ev in events:
                if ev.get("status") == "cancelled":
                    continue
                start = ev.get("start") or {}
                end = ev.get("end") or {}
                start_str = start.get("dateTime") or start.get("date")
                end_str = end.get("dateTime") or end.get("date")
                if not start_str or not end_str:
                    continue
                try:
                    ev_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    ev_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue

                ev_id = ev.get("id", "")
                title = (ev.get("summary") or "Untitled")[:500]

                cur.execute(
                    """INSERT INTO ExternalEvents (user_id, google_event_id, google_calendar_id, title, start_time, end_time, source)
                       VALUES (%s, %s, %s, %s, %s, %s, 'google')
                       ON DUPLICATE KEY UPDATE title = VALUES(title), start_time = VALUES(start_time), end_time = VALUES(end_time)""",
                    (user_id, ev_id, cal_id, title, ev_start, ev_end),
                )
                total_imported += 1

            cur.execute(
                """INSERT INTO UserCalendarConnections (user_id, google_calendar_id, calendar_name, import_date_range_start, import_date_range_end, last_synced_at)
                   VALUES (%s, %s, %s, %s, %s, NOW())
                   ON DUPLICATE KEY UPDATE calendar_name = VALUES(calendar_name), import_date_range_start = VALUES(import_date_range_start),
                   import_date_range_end = VALUES(import_date_range_end), last_synced_at = NOW()""",
                (user_id, cal_id, cal_id[:255], start_dt.date(), end_dt.date()),
            )

        conn.commit()
        return jsonify({"ok": True, "imported_count": total_imported})
    except Exception as e:
        conn.rollback()
        import logging
        logging.getLogger(__name__).warning("Calendar import failed: %s", e)
        return jsonify({"error": "import_failed", "message": str(e)}), 500
    finally:
        conn.close()


@bp.route("/sync", methods=["POST"])
def sync_calendar():
    """Re-fetch events from connected calendars. Full replace per calendar."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    creds = _get_google_credentials(user_id)
    if not creds:
        return jsonify({"error": "calendar_not_connected", "message": "Connect Google Calendar first"}), 401

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT google_calendar_id, import_date_range_start, import_date_range_end
               FROM UserCalendarConnections WHERE user_id = %s""",
            (user_id,),
        )
        connections = cur.fetchall()
    finally:
        conn.close()

    if not connections:
        return jsonify({"error": "no_calendars_connected", "message": "Import calendars first"}), 400

    total_synced = 0
    for conn_row in connections:
        cal_id = conn_row["google_calendar_id"]
        start_d = conn_row.get("import_date_range_start")
        end_d = conn_row.get("import_date_range_end")
        if not start_d or not end_d:
            continue
        time_min = datetime.combine(start_d, datetime.min.time()).isoformat()
        time_max = datetime.combine(end_d, datetime.max.time()).isoformat()

        try:
            from googleapiclient.discovery import build
            service = build("calendar", "v3", credentials=creds)
            events_result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM ExternalEvents WHERE user_id = %s AND google_calendar_id = %s",
                    (user_id, cal_id),
                )
                for ev in events:
                    if ev.get("status") == "cancelled":
                        continue
                    start = ev.get("start") or {}
                    end = ev.get("end") or {}
                    start_str = start.get("dateTime") or start.get("date")
                    end_str = end.get("dateTime") or end.get("date")
                    if not start_str or not end_str:
                        continue
                    try:
                        ev_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        ev_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue
                    ev_id = ev.get("id", "")
                    title = (ev.get("summary") or "Untitled")[:500]
                    cur.execute(
                        """INSERT INTO ExternalEvents (user_id, google_event_id, google_calendar_id, title, start_time, end_time, source)
                           VALUES (%s, %s, %s, %s, %s, %s, 'google')
                           ON DUPLICATE KEY UPDATE title = VALUES(title), start_time = VALUES(start_time), end_time = VALUES(end_time)""",
                        (user_id, ev_id, cal_id, title, ev_start, ev_end),
                    )
                    total_synced += 1
                cur.execute(
                    "UPDATE UserCalendarConnections SET last_synced_at = NOW() WHERE user_id = %s AND google_calendar_id = %s",
                    (user_id, cal_id),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Sync failed for %s: %s", cal_id, e)

    return jsonify({"ok": True, "synced_count": total_synced})


@bp.route("/events", methods=["GET"])
def get_events():
    """Return stored external events for current user. Optional term_id or date range."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    term_id = request.args.get("term_id", type=int)
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        if term_id:
            cur.execute(
                """SELECT id, google_event_id, google_calendar_id, title, start_time, end_time, source, term_id
                   FROM ExternalEvents WHERE user_id = %s AND (term_id = %s OR term_id IS NULL)
                   ORDER BY start_time""",
                (user_id, term_id),
            )
        elif start_date and end_date:
            cur.execute(
                """SELECT id, google_event_id, google_calendar_id, title, start_time, end_time, source, term_id
                   FROM ExternalEvents WHERE user_id = %s AND start_time >= %s AND end_time <= %s
                   ORDER BY start_time""",
                (user_id, start_date, end_date),
            )
        else:
            cur.execute(
                """SELECT id, google_event_id, google_calendar_id, title, start_time, end_time, source, term_id
                   FROM ExternalEvents WHERE user_id = %s ORDER BY start_time""",
                (user_id,),
            )
        rows = cur.fetchall()
        events = []
        for r in rows:
            events.append({
                "id": r["id"],
                "google_event_id": r["google_event_id"],
                "google_calendar_id": r["google_calendar_id"],
                "title": r["title"],
                "start_time": r["start_time"].isoformat() if r.get("start_time") else None,
                "end_time": r["end_time"].isoformat() if r.get("end_time") else None,
                "source": r.get("source", "google"),
            })
        return jsonify({"events": events})
    finally:
        conn.close()


@bp.route("/status", methods=["GET"])
def status():
    """Return whether user has Calendar connected."""
    user_id, err = _get_user_from_token()
    if err:
        return err[0], err[1]

    creds = _get_google_credentials(user_id)
    connected = creds is not None
    return jsonify({"connected": connected})
