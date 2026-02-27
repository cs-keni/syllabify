"""Maintenance mode: read/write AdminSettings. Used by before_request and admin API."""
from app.api.auth import get_db


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
        message = (
            rows.get("maintenance_message") or "Syllabify is undergoing maintenance. Please try again later."
        ).strip() or "Syllabify is undergoing maintenance. Please try again later."
        return enabled, message
    except Exception:
        return False, "Syllabify is undergoing maintenance. Please try again later."
    finally:
        conn.close()


def set_maintenance(enabled, message):
    """Set maintenance mode. Returns True on success."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO AdminSettings (key, value) VALUES ('maintenance_enabled', %s) "
            "ON DUPLICATE KEY UPDATE value = VALUES(value)",
            ("1" if enabled else "0",),
        )
        cur.execute(
            "INSERT INTO AdminSettings (key, value) VALUES ('maintenance_message', %s) "
            "ON DUPLICATE KEY UPDATE value = VALUES(value)",
            (message or "Syllabify is undergoing maintenance. Please try again later.",),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
