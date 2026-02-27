"""AdminSettings helpers: registration toggle, announcement banner."""
from app.api.auth import get_db


def get_admin_setting(key: str, default: str = "") -> str:
    """Read AdminSettings value. Returns default if missing or error."""
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT value FROM AdminSettings WHERE key = %s", (key,))
        row = cur.fetchone()
        return (row["value"] or default).strip() if row else default
    except Exception:
        return default
    finally:
        conn.close()


def set_admin_setting(key: str, value: str) -> bool:
    """Write AdminSettings value. Returns True on success."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO AdminSettings (key, value) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE value = VALUES(value)",
            (key, value or ""),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_registration_enabled() -> bool:
    """True if signups are open. Default True if unset."""
    val = get_admin_setting("registration_enabled", "1")
    return val.lower() in ("1", "true", "yes")


def set_registration_enabled(enabled: bool) -> bool:
    """Set registration open/closed."""
    return set_admin_setting("registration_enabled", "1" if enabled else "0")


def get_announcement_banner() -> str:
    """Announcement text. Empty = no banner."""
    return get_admin_setting("announcement_banner", "")


def set_announcement_banner(text: str) -> bool:
    """Set announcement banner (max 500 chars)."""
    return set_admin_setting("announcement_banner", (text or "")[:500])
