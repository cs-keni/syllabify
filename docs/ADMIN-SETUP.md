# Admin Account Setup Guide

Instructions for group mates to set up and use their Syllabify admin accounts.

---

## Part 1: Becoming an Admin

There are two ways to get admin access, depending on how your project is set up.

### Option A: Pre-created Admin Accounts

If admin accounts were created for you (via `backend/scripts/create_admin_users.py`; the setup person runs this with env vars, no secrets in the repo):

1. **Get your credentials** from whoever set up the app:
   - Username: (your admin will provide yours)
   - Initial password: a temporary password (you’ll change it in Preferences after first login)

2. **Go to the app** at your deployment URL (e.g. `https://your-app.vercel.app` or whatever your frontend URL is).

3. **Log in** with your admin username and the initial password.

4. **Complete security setup** on first login:
   - Answer the security questions
   - Click **Save** to finish

5. **Change your password** in **Preferences**:
   - Open the **Preferences** page from the nav
   - At the top you’ll see **Change password**
   - Enter your current password, then a new password (and confirm)
   - Click **Change password**

---

### Option B: Promote an Existing Account

If you already have a regular Syllabify account and need to be made an admin:

**Option B1: Another admin promotes you**

- Ask an existing admin to:
  1. Open the **Admin** page
  2. Find your username in the user list
  3. Click **Make admin**
- Log out and log back in so your session includes admin status.

**Option B2: Database promotion** (if you have DB access)

- Run this in your MySQL console (Railway, local, etc.):

```sql
UPDATE Users SET is_admin = 1 WHERE username = 'your-username';
```

**Option B3: Environment variable** (for deployment)

- Add your username to `ADMIN_USERNAMES` in the backend env vars:
  - Example: `ADMIN_USERNAMES=admin1,admin2,your-username`
- Redeploy so the change takes effect.

---

## Part 2: Accessing the Admin Panel

1. Log in to Syllabify with your admin account.
2. After security setup, you’ll see the main app (Dashboard, Upload, Schedule, etc.).
3. In the nav bar, click **Admin** (or go to `/app/admin`).
4. You’ll land on the **Control Panel** page.

---

## Part 3: What Admins Can Do

Admins have full access to the app plus the Admin panel. Here’s what you can do there.

### User Management

| Action | Description |
|--------|-------------|
| **List all users** | See every user: id, username, email, security status, admin status, disabled status |
| **Search & filter** | Search by username/email; filter by role (admin/client), status (active/disabled), security (done/pending) |
| **View user details** | Expand a row to see term/course/assignment counts and more |
| **Disable / Enable** | Disable a user so they can’t log in; re-enable when needed |
| **Grant / revoke admin** | Make another user an admin or remove their admin status (you can’t change your own) |
| **Reset security setup** | Clear a user’s security Q&A so they must redo it on next login |
| **Set temporary password** | Set a new password for a user (e.g. after account recovery). **Location:** Expand a user’s row (click the chevron ▶), then use “Set temporary password” in the details panel. |
| **Admin notes** | Add private notes on a user (e.g. “Contacted about duplicate account”) |
| **Delete user** | Permanently delete a user and all their data (requires typing `DELETE` to confirm) |

### Bulk Actions

- **Select multiple users** with the checkboxes.
- **Bulk disable** or **bulk reset security** for all selected users.
- **Keyboard shortcuts** when users are selected:
  - `d` — Disable selected
  - `r` — Reset security for selected
  - `Esc` — Clear selection

### Create Users

- Create new users (e.g. for a class roster) with a temporary password.
- Use **Create user**; they should change the password on first login.

### System Settings

| Setting | Description |
|---------|-------------|
| **Registration** | Turn off new signups when needed; users see “Signups are closed” |
| **Announcement banner** | Show a site-wide message (e.g. downtime notice) |
| **Maintenance mode** | When ON, only admins can use the app; others see a maintenance page |

### Reporting & Audit

| Feature | Description |
|--------|-------------|
| **Export CSV** | Download the user list as CSV |
| **System stats** | View total terms, courses, assignments |
| **Audit log** | View who did what (disable, promote, reset security, etc.) |

---

## Part 4: Quick Reference

- **Admin page**: `/app/admin`
- **First-time admins**: Do security setup and change your password.
- **You can’t**: Disable or delete yourself, or change your own admin status.
- **Maintenance mode**: Only admins can use the app when it’s on; plan accordingly.
- **Audit log**: Admin actions are logged; use it for accountability.

---

## How Users Reset Forgotten Passwords

Syllabify does **not** have a “forgot password” email link. Instead:

1. **User contacts you** (or another admin) because they forgot their password.
2. **You set a temporary password** in the Admin panel:
   - Go to **Admin** → find the user → click the **chevron (▶)** to expand their row
   - In the expanded section, find “Set temporary password (account recovery)”
   - Enter a temporary password (must meet requirements) → click **Set password**
3. **Tell the user** the temporary password (by email, in person, etc.).
4. **User logs in** with the temporary password.
5. **User goes to Preferences** → scroll to **Change password** (top of the page) → sets a new password they choose.

---

## Creating Admin Accounts (for setup person)

To create admin accounts **without storing passwords in the repo**:

```bash
cd backend
ADMIN_INITIAL_PASSWORD="YourTempPassword123!" ADMIN_USERNAMES="admin-user1,admin-user2" python scripts/create_admin_users.py
```

- Set `ADMIN_INITIAL_PASSWORD` to a temporary password (min 8 chars). Never commit this value.
- Set `ADMIN_USERNAMES` to comma-separated usernames.
- Admins should change their password in Preferences after first login.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| No Admin link in nav | Log out and log back in; if it still doesn’t appear, your account may not be admin yet |
| “Forbidden” on Admin page | Your session may not have admin status; try logging out and back in |
| Forgot password | Ask another admin to set a temporary password for you (Admin → expand your row → Set temporary password) |
| Maintenance mode is on | Only admins can log in; if you’re an admin, log in as usual |
