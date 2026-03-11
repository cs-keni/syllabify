"""
Create admin accounts. Requires MySQL connection (DB_* env vars).

Usage:
  cd backend && ADMIN_INITIAL_PASSWORD=your-temp-pw ADMIN_USERNAMES=user1,user2 python scripts/create_admin_users.py

  Or with separate env:
    export ADMIN_INITIAL_PASSWORD="YourTempPassword123!"
    export ADMIN_USERNAMES="admin-user1,admin-user2"
    python scripts/create_admin_users.py

Never commit ADMIN_INITIAL_PASSWORD. Admins should change their password in Preferences after first login.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.auth import get_db, hash_password


def main():
    password = os.environ.get("ADMIN_INITIAL_PASSWORD")
    usernames_str = os.environ.get("ADMIN_USERNAMES", "")

    if not password or len(password) < 8:
        print(
            "Set ADMIN_INITIAL_PASSWORD (min 8 chars) and ADMIN_USERNAMES (comma-separated).\n"
            "Example: ADMIN_INITIAL_PASSWORD=TempPass123! ADMIN_USERNAMES=admin1,admin2 python scripts/create_admin_users.py"
        )
        sys.exit(1)

    usernames = [u.strip() for u in usernames_str.split(",") if u.strip()]
    if not usernames:
        print("ADMIN_USERNAMES is empty. Example: ADMIN_USERNAMES=admin1,admin2")
        sys.exit(1)

    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        hashed = hash_password(password)
        for username in usernames:
            cur.execute("SELECT id FROM Users WHERE username = %s", (username,))
            if cur.fetchone():
                print(f"  Skip {username} (already exists)")
                continue
            cur.execute(
                "INSERT INTO Users (username, password_hash, security_setup_done, is_admin) "
                "VALUES (%s, %s, FALSE, TRUE)",
                (username, hashed),
            )
            print(f"  Created {username} (id={cur.lastrowid})")
        conn.commit()
        print("Done. Admins should change their password in Preferences.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
