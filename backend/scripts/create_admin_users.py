"""
Create admin accounts. Requires MySQL connection.

Option A - SQL (no local MySQL needed): Run docker/migrations/006_admin_users.sql
  in Railway's MySQL Query tab. Copy the INSERT statements and execute.

Option B - Python (requires DB env vars and MySQL reachable):
  cd backend && PYTHONPATH=. python scripts/create_admin_users.py

Creates Users with is_admin=1. Skips if username already exists.
"""
import sys
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.auth import get_db, hash_password

ADMINS = [
    ("admin-andrew", "Changeme123!"),
    ("admin-leon", "Changeme123!"),
    ("admin-saintgeorge", "Changeme123!"),
    ("admin-kenny", "Changeme123!"),
]


def main():
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        for username, password in ADMINS:
            cur.execute("SELECT id FROM Users WHERE username = %s", (username,))
            if cur.fetchone():
                print(f"  Skip {username} (already exists)")
                continue
            hashed = hash_password(password)
            cur.execute(
                "INSERT INTO Users (username, password_hash, security_setup_done, is_admin) "
                "VALUES (%s, %s, FALSE, TRUE)",
                (username, hashed),
            )
            print(f"  Created {username} (id={cur.lastrowid})")
        conn.commit()
        print("Done. Admins can log in and should change their password in Preferences.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
