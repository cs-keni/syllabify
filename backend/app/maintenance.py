"""Maintenance mode: read/write AdminSettings. Used by before_request and admin API."""
import logging

from app.api.auth import get_db

_DEFAULT_MSG = "Syllabify is undergoing maintenance. Please try again later."

logger = logging.getLogger(__name__)


def get_maintenance_status():
    """Returns (enabled: bool, message: str). If table missing, (False, default message)."""
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT key, value FROM AdminSettings WHERE key IN ('maintenance_enabled', 'maintenance_message')"
        )
        rows = {r["key"]: r["value"] for r in cur.fetchall()}
        enabled = (rows.get("maintenance_enabled") or "0").strip() in ("1", "true", "yes")
        message = (rows.get("maintenance_message") or _DEFAULT_MSG).strip() or _DEFAULT_MSG
        return enabled, message
    except Exception as e:
        logger.warning("Failed to read maintenance status: %s", e)
        return False, _DEFAULT_MSG
    finally:
        conn.close()


def set_maintenance(enabled, message):
    """Set maintenance mode. Returns True on success."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO AdminSettings (key, value) VALUES ('maintenance_enabled', %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            ("1" if enabled else "0",),
        )
        cur.execute(
            "INSERT INTO AdminSettings (key, value) VALUES ('maintenance_message', %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (message or _DEFAULT_MSG,),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning("Failed to set maintenance mode: %s", e)
        return False
    finally:
        conn.close()
