"""Admin audit log. Records who did what, when."""
from app.api.auth import get_db


def log_admin_action(
    admin_id: int,
    admin_username: str,
    action: str,
    target_user_id: int | None = None,
    target_username: str | None = None,
    details: str | None = None,
) -> None:
    """Log an admin action. Silently ignores DB errors so audit never blocks operations."""
    try:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO AdminAuditLog
                   (admin_user_id, admin_username, action, target_user_id, target_username, details)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    admin_id,
                    (admin_username or "")[:50],
                    (action or "")[:50],
                    target_user_id,
                    (target_username or "")[:50] if target_username else None,
                    details[:2000] if details else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # Never let audit logging block admin operations
