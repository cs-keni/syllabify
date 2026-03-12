# Google OAuth Setup Guide

This guide walks you through setting up **Google Sign-In** and **Google Calendar Import** for Syllabify when using **Render** (backend), **Vercel** (frontend), and **Railway** (database).

---

## Overview

| What                   | Where                                             |
| ---------------------- | ------------------------------------------------- |
| **Database migration** | Run once on Railway MySQL                         |
| **Backend env vars**   | Render (syllabify-api)                            |
| **Frontend env vars**  | Vercel                                            |
| **Google Cloud**       | Create OAuth credentials, configure redirect URIs |

---

## Part 1: Google Cloud Console

### Step 1.1 – Create a project (if you don’t have one)

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown (top left) → **New Project**.
3. Name it (e.g. `Syllabify`) and click **Create**.

### Step 1.2 – Enable APIs

1. In the left menu: **APIs & Services** → **Library**.
2. Search for **Google Calendar API** → click it → **Enable**.
3. (Optional) Search for **Google Identity Services** – no need to enable; it’s used for Sign-in.

### Step 1.3 – Configure OAuth consent screen

1. **APIs & Services** → **OAuth consent screen**.
2. Choose **External** (or Internal if using a Google Workspace org).
3. Fill in:
   - **App name**: Syllabify
   - **User support email**: your email
   - **Developer contact**: your email
4. Click **Save and Continue**.
5. **Scopes**: Click **Add or Remove Scopes**.
   - Add: `.../auth/userinfo.email`
   - Add: `.../auth/userinfo.profile`
   - Add: `openid`
   - Add: `https://www.googleapis.com/auth/calendar.readonly` (for Calendar import)
6. Click **Save and Continue**.
7. **Test users** (if in Testing mode): Add your email so you can sign in during development.
8. Click **Back to Dashboard**.

### Step 1.4 – Create OAuth 2.0 credentials

1. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**.
2. **Application type**: **Web application**.
3. **Name**: e.g. `Syllabify Web`.
4. **Authorized JavaScript origins** – add:
   - `http://localhost:5173` (local dev)
   - `https://your-app.vercel.app` (production – replace with your real Vercel URL)
   - `https://your-app-dev.vercel.app` (dev deployment, if you have one)
5. **Authorized redirect URIs** – add:
   - `http://localhost:5000/api/calendar/callback` (local backend)
   - `https://syllabify-api.onrender.com/api/calendar/callback` (production – replace with your Render URL)
   - `https://syllabify-api-dev.onrender.com/api/calendar/callback` (dev backend, if you have one)
6. Click **Create**.
7. Copy the **Client ID** and **Client Secret**. You’ll use these in Render and Vercel.

---

## Part 2: Database migration (Railway)

Run the migration **once** on your Railway MySQL database.

### Option A – Railway Query UI

1. Go to [Railway](https://railway.app) → your project → **MySQL** service.
2. Open **Data** or **Query** (or **Connect** → **Query**).
3. Open `docker/migrations/011_google_oauth_calendar.sql` in your repo.
4. Copy the entire file contents.
5. Paste into Railway’s query box and run it.
6. You should see success for each statement. If you get “Duplicate column” for `google_id` or `auth_provider`, those columns already exist – you can skip those lines or ignore the error.

### Option B – MySQL CLI

From your machine (if `mysql` is installed):

```bash
mysql -h YOUR_RAILWAY_PUBLIC_HOST -P YOUR_RAILWAY_PUBLIC_PORT -u root -p YOUR_DATABASE < docker/migrations/011_google_oauth_calendar.sql
```

Replace `YOUR_RAILWAY_PUBLIC_HOST`, `YOUR_RAILWAY_PUBLIC_PORT`, `YOUR_DATABASE`, and the password with your Railway public connection values.

---

## Part 3: Environment variables

### 3.1 – Render (backend)

1. Go to [Render Dashboard](https://dashboard.render.com) → your **syllabify-api** Web Service.
2. Open **Environment** (or **Environment Variables**).
3. Add these variables:

| Key                    | Value                                                      | Secret? |
| ---------------------- | ---------------------------------------------------------- | ------- |
| `GOOGLE_CLIENT_ID`     | Your Google OAuth Client ID (from Step 1.4)                | No      |
| `GOOGLE_CLIENT_SECRET` | Your Google OAuth Client Secret (from Step 1.4)            | **Yes** |
| `GOOGLE_REDIRECT_URI`  | `https://syllabify-api.onrender.com/api/calendar/callback` | No      |

**Important:** Replace `syllabify-api.onrender.com` with your actual Render backend URL.

4. Click **Save Changes**. Render will redeploy the backend.

**For dev deployment** (syllabify-api-dev): Add the same three variables, but set `GOOGLE_REDIRECT_URI` to `https://syllabify-api-dev.onrender.com/api/calendar/callback`.

---

### 3.2 – Vercel (frontend)

1. Go to [Vercel](https://vercel.com) → your Syllabify project.
2. Open **Settings** → **Environment Variables**.
3. Add:

| Name                    | Value                                                    | Environment                          |
| ----------------------- | -------------------------------------------------------- | ------------------------------------ |
| `VITE_GOOGLE_CLIENT_ID` | Your Google OAuth Client ID (same as `GOOGLE_CLIENT_ID`) | Production (and Preview if you want) |

4. Save.
5. Go to **Deployments** → open the **⋯** menu on the latest deployment → **Redeploy**.  
   (Vite bakes env vars at build time, so a redeploy is required.)

**For dev deployment** (syllabify-dev): Add the same variable to that project.

---

### 3.3 – Railway

You do **not** add Google OAuth variables to Railway. Railway only hosts the database; the backend (Render) holds the OAuth credentials.

---

## Part 4: Local development (optional)

If you run the app locally:

1. Copy `.env.example` to `backend/.env` (or repo root `.env` if that’s where Flask reads it).
2. Add:
   ```
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:5000/api/calendar/callback
   ```
3. Create `frontend/.env.local` with:
   ```
   VITE_API_URL=http://localhost:5000
   VITE_GOOGLE_CLIENT_ID=your-client-id
   ```

---

## Part 5: Checklist

Use this to confirm everything is done:

- [ ] **Google Cloud**
  - [ ] Project created
  - [ ] Google Calendar API enabled
  - [ ] OAuth consent screen configured (app name, scopes)
  - [ ] OAuth 2.0 Web client created
  - [ ] Authorized JavaScript origins include your Vercel URL(s)
  - [ ] Authorized redirect URIs include your Render URL(s) + `/api/calendar/callback`
  - [ ] Client ID and Client Secret copied

- [ ] **Railway**
  - [ ] Migration `011_google_oauth_calendar.sql` run once on production MySQL
  - [ ] (If dev) Same migration run on dev MySQL

- [ ] **Render**
  - [ ] `GOOGLE_CLIENT_ID` set
  - [ ] `GOOGLE_CLIENT_SECRET` set (as Secret)
  - [ ] `GOOGLE_REDIRECT_URI` = `https://YOUR-RENDER-URL/api/calendar/callback`
  - [ ] Backend redeployed after adding env vars

- [ ] **Vercel**
  - [ ] `VITE_GOOGLE_CLIENT_ID` set (same as `GOOGLE_CLIENT_ID`)
  - [ ] Frontend redeployed after adding env var

---

## Part 6: Troubleshooting

### “Google sign-in is not configured”

- `GOOGLE_CLIENT_ID` is missing or empty on Render. Add it and redeploy.

### “Sign in with Google” button doesn’t appear

- `VITE_GOOGLE_CLIENT_ID` is missing or empty on Vercel. Add it and **redeploy** (env vars are baked in at build time).

### “invalid Google token” after clicking Sign in

- Client ID mismatch: `VITE_GOOGLE_CLIENT_ID` (frontend) must match `GOOGLE_CLIENT_ID` (backend).
- Google Cloud: ensure your Vercel URL is in **Authorized JavaScript origins**.

### “Failed to connect Google Calendar” / redirect fails

- `GOOGLE_REDIRECT_URI` on Render must exactly match the URL in Google Cloud **Authorized redirect URIs** (including `/api/calendar/callback`).
- No trailing slash on the redirect URI.

### “redirect_uri_mismatch” from Google

- The redirect URI in the request does not match what’s configured in Google Cloud. Check:
  - Render: `GOOGLE_REDIRECT_URI` = `https://your-app.onrender.com/api/calendar/callback`
  - Google Cloud: same URL listed under **Authorized redirect URIs**.

### “Database migration required”

- Run `docker/migrations/011_google_oauth_calendar.sql` on your Railway MySQL (see Part 2).

---

## Summary

| Platform    | Variables to add                                                  |
| ----------- | ----------------------------------------------------------------- |
| **Render**  | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |
| **Vercel**  | `VITE_GOOGLE_CLIENT_ID`                                           |
| **Railway** | None (run migration only)                                         |

After setup, users can sign in with Google on the Login and Register pages, and use “Connect Google Calendar” and “Import” on the Schedule page.
