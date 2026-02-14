# Syllabify Deployment Guide

This guide covers deploying **Syllabify** with **two deployments** (no `.env` sharing in a multi-user team):

- **Production (main branch)** → one Vercel + one Render + one Railway MySQL. This is the live app.
- **Dev (dev branch)** → a second Vercel project + second Render service + second Railway MySQL. The team tests here before merging to main.

Each deployment uses:

- **Frontend** → [Vercel](https://vercel.com) (`*.vercel.app` URL)
- **Backend** → [Render](https://render.com) (free tier; sleeps when idle)
- **Database** → [Railway](https://railway.app) MySQL (free tier credit)

You do **not** need a custom domain. No one shares database logins or `.env` files; credentials live only in each platform’s dashboard.

---

**Railway “Connect”: Private or Public?**  
Choose **Public Network**. Your backend runs on Render (outside Railway), so it must reach MySQL over the internet. Private Network only allows other Railway services in the same project.

---

## Prerequisites

- GitHub repo with your Syllabify code
- Accounts: [Vercel](https://vercel.com), [Render](https://render.com), [Railway](https://railway.app)
- (Optional) Docker installed locally only if you want to run backend + DB locally with `docker-compose`

**Do you need a `.env` file for production or dev deployments?** No. Render, Vercel, and Railway use the environment variables you set in their dashboards. You do **not** create or upload a `.env` file. Use `.env` only for optional local development (copy from `.env.example` and never commit it).

**Overview**

| Deployment   | Branch | Frontend (Vercel)     | Backend (Render)   | Database (Railway) |
|-------------|--------|------------------------|--------------------|--------------------|
| **Production** | `main` | e.g. syllabify-iota.vercel.app      | e.g. syllabify-api.onrender.com  | Production MySQL   |
| **Dev**        | `dev`  | e.g. syllabify-dev.vercel.app | e.g. syllabify-api-dev.onrender.com | Dev MySQL (separate) |

Sections 1–3 set up **production** (main). Section 4 sets up the **dev** deployment. Section 5 is optional local development.

---

## 1. Production: Database (MySQL on Railway)

Your backend runs on **Render**, not on Railway. So the database must accept connections from the **internet**. That’s why we use **Public Network** below.

### Step 1.1 – Create the MySQL service

1. Go to [Railway](https://railway.app) and sign in (e.g. with GitHub).
2. Click **New Project**.
3. Choose **Deploy MySQL** (or **Add a plugin** / **MySQL** template). Railway will create a project with one MySQL service.
4. Click on the **MySQL** service to open it.

### Step 1.2 – Connect: choose Public Network

5. In the MySQL service, find the **Connect** (or **Networking** / **Settings**) area. You may see a prompt to connect the database.
6. When Railway asks how to connect, you’ll see two options:
   - **Private Network** – only other services in the *same* Railway project can reach the database. **Do not use this** for Syllabify, because the backend runs on Render.
   - **Public Network** – Railway gives you a public host and port so anything on the internet (including Render) can connect with your username/password.
7. **Choose “Public Network”** (or “Public” / “Enable public networking” / “TCP proxy”, depending on Railway’s wording). Your backend on Render needs this to reach MySQL.
8. After enabling public access, Railway will show connection details (host, port, user, password, database). Keep this tab open or copy the values somewhere safe.

### Step 1.3 – Get the connection variables (for Render)

9. You do **not** need to connect Railway to your GitHub repo. The MySQL service is standalone; Render will connect to it using the credentials below.
10. Open the **Variables** tab for the MySQL service. Railway shows two kinds of values:
    - **Internal** (only work from inside Railway): `MYSQLHOST` = `mysql.railway.internal`, `MYSQLPORT` = `3306`. **Do not use these for Render** – Render is outside Railway and cannot reach `*.railway.internal`.
    - **Public** (work from the internet, including Render): these come from the **connection URL** or **Public Network** section. The URL looks like:
      `mysql://USER:PASSWORD@HOST:PORT/DATABASE`
11. From that **public** URL, read off (or copy from the Variables tab if Railway lists them):
    - **DB_HOST** = public host (e.g. `maglev.proxy.rlwy.net` – the part after `@` and before `:` in the URL)
    - **DB_PORT** = public port (e.g. `35428` – the number after the host in the URL; **not** `3306` if the URL shows something else)
    - **DB_USER** = user (often `root`) → from `MYSQLUSER`
    - **DB_PASSWORD** = password → from `MYSQLPASSWORD` (or from the URL)
    - **DB_NAME** = database name (e.g. `railway`) → from `MYSQLDATABASE` (Railway may spell it `MYSQLDATABSE`; use the value, e.g. `railway`)
12. Save these five values somewhere safe. You will paste them into **Render** in Section 2. **Important:** Use the **public** host and **public** port (from the connection URL), not `MYSQLHOST` / `MYSQLPORT` (those are internal).

### Step 1.4 – Initialize the schema (one-time)

13. Your app needs four tables: `Users`, `UserSecurityAnswers`, `Schedules`, `Assignments`. You only need to run the SQL **once** against your Railway MySQL. **No Docker or MySQL install required** – use Option A.

**Option A – Railway’s web UI (no Docker, no mysql install; recommended)**  
- In [Railway](https://railway.app), open your project → click your **MySQL** service.
- Look for a **Data** tab, or **Query**, or **Connect** → **Query** (Railway’s wording may vary). If you see a place to run SQL or “Open in Data Browser,” use it.
- Open the file **`docker/init.sql`** in your repo in an editor. **Select all** and copy the entire contents (all the `CREATE TABLE ...` statements).
- Paste into Railway’s SQL / query box and run it (e.g. **Run** or **Execute**). You should see success or “Query OK” for each table. Then you’re done.
- If you don’t see a Query/Data option, try **Connect** and see if there’s a “Web client” or link to a query UI; or use Option B or D.

**Option B – Use Docker (only if Docker Desktop is installed and running)**  
- The error `failed to connect to the docker API ... check if the daemon is running` means Docker isn’t installed or Docker Desktop isn’t started. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and start it, then try again.
- Run from your **syllabify repo root** (the folder that contains `docker/init.sql`). If you’re in `syllabify/docker`, run `cd ..` first.
- **Piping the file** (no volume mount – works on Windows with OneDrive/paths with spaces). Replace host, port, and password with your Railway **public** values:

  ```bash
  docker run --rm -i mysql:8.0 mysql -h maglev.proxy.rlwy.net -P 35428 -u root -pYOUR_PASSWORD railway < docker/init.sql
  ```

  No space between `-p` and the password. The host reads `docker/init.sql` and pipes it into the container, so no `-v` mount is needed.

**Option C – From your computer (only if the `mysql` command is installed)**  
- The `mysql` CLI is **not** the same as `npm install mysql`. Install the real MySQL client (e.g. [MySQL Installer](https://dev.mysql.com/downloads/installer/)) or use WSL. From **syllabify repo root**: `mysql -h PUBLIC_HOST -P PUBLIC_PORT -u root -p railway`, then at `mysql>` run `source docker/init.sql`.

**Option D – Skip for now**  
- Continue to Section 2. After the backend is on Render, the first login may fail with “table doesn’t exist.” Then run Option A and redeploy.

14. After the schema is created, you’re done with **production** Railway. Save the connection details as “production DB”; you’ll create a **separate** MySQL for dev in Section 4. Move on to Section 2 (Render) and use the **public** host, **public** port, user, password, and database name from Step 1.3.

---

## 2. Production: Backend (Flask on Render)

Render’s free tier spins down after ~15 minutes of no traffic; the first request after that may take up to ~1 minute to wake (cold start).

### Step 2.1 – Create the Web Service

1. Go to [Render Dashboard](https://dashboard.render.com) and sign in (e.g. with GitHub).
2. Click **New** (or **Create**) → **Web Service**.
3. If asked, **connect your GitHub account** and authorize Render to see your repos. Select the **syllabify** repository (the one that contains `backend/` and `frontend/`).
4. Fill in the form. Use these exact choices where they appear:
   - **Name**: e.g. `syllabify-api` (you’ll get a URL like `https://syllabify-api.onrender.com`). This is the **production** backend.
   - **Region**: pick one (e.g. Oregon).
   - **Branch**: **`main`** (production only; dev backend is created in Section 4).
   - **Root Directory**: leave **blank** (Render uses the repo root).
   - **Runtime**: choose **Docker** (not “Python” or “Node”). This tells Render to build and run using your `backend/Dockerfile`.
   - **Dockerfile Path**: leave **blank**. The repo has a **`Dockerfile` at the repo root** (same content as `backend/Dockerfile`) so Render finds it. If Render still can’t find it, ensure Root Directory is blank.
5. Do **not** deploy yet. Click **Advanced** or scroll down to **Environment Variables** first (Step 2.2).

### Step 2.2 – Add environment variables (before first deploy)

6. In the same Web Service form, find **Environment** or **Environment Variables**.
7. Add each variable below. Use the **Key** exactly as written; for **Value**, use the source indicated. If Render has a “Secret” toggle for sensitive values, turn it on for `DB_PASSWORD` and `SECRET_KEY`.

| Key           | Where to get the value |
|---------------|------------------------|
| `DB_HOST`     | **Public** host from Railway (e.g. from the connection URL: `maglev.proxy.rlwy.net`). **Not** `MYSQLHOST` (that’s internal). |
| `DB_PORT`     | **Public** port from Railway (e.g. from the connection URL: `35428`). **Not** `MYSQLPORT` (3306) – that’s internal. |
| `DB_NAME`     | From Railway: `MYSQLDATABASE` (value is often `railway`). |
| `DB_USER`     | From Railway: `MYSQLUSER` (often `root`). |
| `DB_PASSWORD` | From Railway: `MYSQLPASSWORD`. (Mark as Secret.) |
| `SECRET_KEY`  | Generate one: run `openssl rand -hex 32` in a terminal, or use any long random string. (Mark as Secret.) |
| `FRONTEND_URL`| Leave blank for now. After you deploy the frontend (Section 3), come back and set this to your Vercel URL, e.g. `https://syllabify-xxx.vercel.app` (no trailing slash). Then trigger a redeploy. |

- Do **not** add `PORT`. Render sets it automatically; the Dockerfile uses it.
- Optional later: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRATION_DELTA`, Google OAuth vars – only if your code uses them.

### Step 2.3 – Deploy and copy the backend URL

8. Click **Create Web Service** (or **Save**). Render will build the Docker image from `backend/Dockerfile` and start the app. Wait until the deploy status is **Live** (or green).
9. At the top of the service page you’ll see a URL like `https://syllabify-api.onrender.com`. **Copy this URL** – you’ll paste it into Vercel in Section 3 as `VITE_API_URL`.

---

## 3. Production: Frontend (Vite/React on Vercel)

### Step 3.1 – Create the project and connect the repo

1. Go to [Vercel](https://vercel.com) and sign in (e.g. with GitHub).
2. Click **Add New** → **Project** (or **Import Project**).
3. If asked, **import** or **connect** the **syllabify** repository from GitHub. Select it and click **Import**.

### Step 3.2 – Configure build (Root Directory = frontend)

4. On the “Configure Project” screen, set these **exactly**:
   - **Framework Preset**: **Vite** (Vercel usually detects it; if not, choose Vite).
   - **Root Directory**: click **Edit** and set it to **`frontend`**. This is required so Vercel builds the React app, not the whole repo.
   - **Production Branch**: **`main`** (in Settings → Git after creation if not shown here). Only the main branch should deploy to this project’s production URL.
   - **Build Command**: leave as `npm run build` (Vite default).
   - **Output Directory**: leave as `dist` (Vite default).
   - **Install Command**: leave as `npm install`.
5. **Before** clicking Deploy, expand **Environment Variables** (if shown) and add one variable:
   - **Name**: `VITE_API_URL`
   - **Value**: paste the **Render backend URL** you copied in Step 2.3 (e.g. `https://syllabify-api.onrender.com`). No trailing slash.
   - Apply to **Production** (and **Preview** if you want preview deploys to use the same API).

### Step 3.3 – Deploy and copy the frontend URL

6. Click **Deploy**. Vercel will build the frontend and host it. Wait until the deploy finishes.
7. You’ll see a URL like `https://syllabify-xxx.vercel.app`. **Copy this URL** – you’ll use it in Step 3.4.

### Step 3.4 – Point the backend at the frontend (CORS)

8. Go back to **Render** → your **syllabify-api** Web Service.
9. Open **Environment** (or **Environment Variables**).
10. Find **FRONTEND_URL**. If you left it blank earlier, add it now. If it’s already there, edit it. Set the value to the **Vercel URL** you copied (e.g. `https://syllabify-xxx.vercel.app`), **no trailing slash**.
11. Save. Render will redeploy the backend so CORS allows your frontend origin.
12. After the redeploy is **Live**, open your Vercel URL in a browser and try logging in (e.g. `syllabify-client` / `ineedtocutmytoenails422`) to confirm the app talks to the backend.

**If you added `VITE_API_URL` after the first deploy:** go to Vercel → your project → **Deployments** → open the **⋯** menu on the latest deployment → **Redeploy**. This rebuilds the app with the correct API URL.

---

## 4. Dev deployment (dev branch)

This section creates a **second** deployment so the team can test the **dev** branch at a live URL. No one shares `.env` or database logins; dev uses its own Railway MySQL, Render service, and Vercel project.

### 4.1 – Dev database (Railway, second MySQL)

1. In [Railway](https://railway.app), create a **new project** (or add a second MySQL to an existing one). This keeps dev data separate from production.
2. Choose **Deploy MySQL** (or Add MySQL). Open the MySQL service.
3. Enable **Public Network** (same as production). Copy the **public** connection URL and variables (host, port, user, password, database name). Label these as **dev DB**.
4. Run the schema **once** on this dev database: open **`docker/init.sql`** in the repo, copy all `CREATE TABLE` statements, and run them in Railway’s Query/Data UI for this MySQL service (same as Section 1.4, Option A).

### 4.2 – Dev backend (Render, second Web Service)

5. In [Render](https://dashboard.render.com), click **New** → **Web Service**.
6. Select the **syllabify** repo. Configure:
   - **Name**: e.g. `syllabify-api-dev` (URL will be `https://syllabify-api-dev.onrender.com`).
   - **Branch**: **`dev`** (not main).
   - **Root Directory**: blank.
   - **Runtime**: **Docker**. **Dockerfile Path**: blank.
7. **Environment Variables**: add the same keys as production, but use **dev** values:
   - **DB_HOST**, **DB_PORT**, **DB_NAME**, **DB_USER**, **DB_PASSWORD** → from the **dev** Railway MySQL (public values).
   - **SECRET_KEY** → generate a new one for dev (e.g. `openssl rand -hex 32`). Mark as Secret.
   - **FRONTEND_URL** → leave blank for now; set after 4.3.
8. Create the service. Wait until **Live**, then copy the dev backend URL (e.g. `https://syllabify-api-dev.onrender.com`). You’ll use it in the next step.

### 4.3 – Dev frontend (Vercel, second project)

9. In [Vercel](https://vercel.com), click **Add New** → **Project** and import the **syllabify** repo again (same repo, second project).
10. Configure the project:
    - **Project Name**: e.g. `syllabify-dev` (you’ll get a URL like `https://syllabify-dev-xxx.vercel.app`).
    - **Root Directory**: **`frontend`**.
    - **Production Branch**: set to **`dev`** (in Configure or later in Settings → Git). This project’s production URL will then always reflect the dev branch.
    - **Framework**: Vite. Build/Output: leave defaults.
11. **Environment Variables** (before Deploy):
    - **Name**: `VITE_API_URL`
    - **Value**: the **dev** Render URL from step 8 (e.g. `https://syllabify-api-dev.onrender.com`). No trailing slash.
    - Apply to **Production** (for this project, “Production” means the dev branch).
12. Deploy. Copy the dev frontend URL (e.g. `https://syllabify-dev-xxx.vercel.app`).

### 4.4 – Wire dev backend CORS to dev frontend

13. In **Render** → your **syllabify-api-dev** service → **Environment**.
14. Set **FRONTEND_URL** to the **dev** Vercel URL from step 12 (no trailing slash). Save so the dev backend redeploys.
15. When the redeploy is **Live**, open the dev Vercel URL in a browser and test (e.g. login). Dev deployment is done.

**Workflow:** Feature branches → PR into **dev** → team tests at the **dev** URL → when ready, PR **dev → main**. Production (main) and dev stay separate; no shared credentials.

---

## 5. Optional: Local development

If you want to run the app on your machine (e.g. backend + DB via `docker-compose`, frontend via `npm run dev`), use **Section 4** in the repo’s previous version of this doc or the short steps in the README. For a multi-user team, prefer testing on the **dev deployment** URL so no one needs to share `.env` or database logins.

---

## 6. Checklist

**Production (main)**

- [ ] **Railway (prod)**: MySQL created → **Public Network** → Variables copied → `docker/init.sql` run once.
- [ ] **Render (prod)**: Web Service, branch **main** → DB_*, SECRET_KEY set → deploy Live → backend URL copied.
- [ ] **Vercel (prod)**: Project, branch **main**, root **frontend** → `VITE_API_URL` = prod Render URL → deploy → frontend URL copied.
- [ ] **Render (prod)**: `FRONTEND_URL` = prod Vercel URL → redeploy.
- [ ] **Test prod**: Open prod Vercel URL → login → confirm API works.

**Dev (dev branch)**

- [ ] **Railway (dev)**: Second MySQL → Public Network → run `docker/init.sql` → copy dev DB variables.
- [ ] **Render (dev)**: Second Web Service, branch **dev** → dev DB_*, new SECRET_KEY → deploy Live → copy dev backend URL.
- [ ] **Vercel (dev)**: Second project, branch **dev**, root **frontend** → `VITE_API_URL` = dev Render URL → deploy → copy dev frontend URL.
- [ ] **Render (dev)**: `FRONTEND_URL` = dev Vercel URL → redeploy.
- [ ] **Test dev**: Open dev Vercel URL → login → confirm dev API works.

---

## 7. Troubleshooting

- **“open Dockerfile: no such file or directory” on Render**  
  The repo has a **`Dockerfile` at the repo root** (same as `backend/Dockerfile`) so Render finds it. Ensure **Root Directory** is blank and **Dockerfile Path** is blank (so Render uses the root `Dockerfile`). Commit and push the root `Dockerfile`, then trigger a **Manual Deploy**.

- **CORS errors in browser**  
  Ensure Render has `FRONTEND_URL` exactly equal to your Vercel URL (no trailing slash). Backend uses this for `CORS(app, origins=...)`.

- **Backend “Application failed to respond”**  
  Free tier may be spinning up (wait ~1 min and retry). Also check Render **Logs** for crashes and that `DB_*` and `SECRET_KEY` are set.

- **Login returns 502 (Bad Gateway)**  
  The request reached Render but the backend crashed or errored. In Render → your service → **Logs**, look at the time of the login attempt for a Python traceback (e.g. DB connection error, missing env var). Common cause: **DB_HOST**, **DB_PORT**, **DB_NAME**, **DB_USER**, **DB_PASSWORD** not set on Render (copy from Railway's **public** values). Also ensure **SECRET_KEY** is set.

- **Database connection errors**  
  Confirm Railway MySQL is running and that `DB_HOST` / `DB_PORT` are correct (Railway’s public host/port if connecting from Render). If Railway uses a private network and Render is outside, use Railway’s **Public Networking** (TCP proxy) and the host/port they give for external connections.

- **"Lost connection to MySQL server at 'reading initial communication packet'" (500 on login)**  
  This means Render cannot reach Railway's MySQL. Common causes:
  - **Railway MySQL is stuck or degraded** – If Railway's database view shows "Database Connection: failing" or "container is starting up or transitioning," the MySQL service may be in a bad state.
  - **Fix: Redeploy the MySQL service** – In Railway → your project → MySQL service → **Settings** or **⋯** menu → **Redeploy** (or **Restart**). Wait a few minutes for the container to fully start. Then retry login.
  - **Verify connection variables** – On Render, ensure `DB_HOST` and `DB_PORT` are the **public** values from Railway's **Connect** / **Networking** tab (e.g. `maglev.proxy.rlwy.net` and `35428`), **not** `MYSQLHOST` / `MYSQLPORT` (internal).
  - **If it keeps failing** – Railway's free-tier MySQL can be unreliable. Consider migrating to a more stable option (e.g. [PlanetScale](https://planetscale.com), [Neon](https://neon.tech), or [Supabase](https://supabase.com)) if redeploys don't resolve it.

- **Frontend shows wrong API**  
  `VITE_API_URL` is baked in at **build** time. Change it in Vercel, then trigger a new deploy.

- **Login: "Failed to fetch"**  
  See **Debugging "Failed to fetch"** below.

### Debugging "Failed to fetch" (login or any API call)

1. **Browser DevTools**  
   Open your Vercel site, right-click, **Inspect**, **Network** tab. Try logging in again. Find the request to `/api/auth/login`. Check:
   - **Request URL**: Should be `https://syllabify-api.onrender.com/api/auth/login`. If it shows `http://localhost:5000/...`, the frontend was built without `VITE_API_URL` – set it in Vercel and **redeploy**.
   - **Status**: (failed) or CORS usually means wrong API URL or CORS. In **Console** look for CORS or "blocked" messages.

2. **Vercel: VITE_API_URL**  
   Vite bakes env at **build** time. Vercel → project → **Settings** → **Environment Variables**: set **VITE_API_URL** = `https://syllabify-api.onrender.com` (no trailing slash). Then **Deployments** → menu on latest → **Redeploy**.

3. **Render: FRONTEND_URL**  
   **FRONTEND_URL** is a **backend** variable – set it on **Render**, not Vercel. Render → your backend → **Environment**: set **FRONTEND_URL** = `https://syllabify-iota.vercel.app` (your Vercel URL, no trailing slash). Save so it redeploys. Without this, CORS blocks the response and you get "Failed to fetch".

4. **Render cold start**  
   Free tier sleeps after ~15 min. First request can take 30–60 s; the browser may time out. Open `https://syllabify-api.onrender.com/` in a new tab, wait until you see "sample index text", then try login again.

5. **Login in DB**  
   You do **not** add the user manually. The app creates the dev user on first successful login. "Failed to fetch" is network/CORS, not "user not in DB".

6. **Backend logs**  
   Render → service → **Logs**. After a login attempt check for errors. If the backend logged a 200 but the browser still says "Failed to fetch", CORS blocked the response – fix FRONTEND_URL (step 3).

---

## 8. Docker (what’s used where)

- **Local**: `docker-compose.yml` runs MySQL + backend for development.
- **Render**: Builds and runs the **backend** only via `backend/Dockerfile` (production server and `PORT`).
- **Vercel**: Does **not** use your Dockerfile; it builds the frontend with its own Vite build.
- **Railway**: Hosts MySQL only; no Docker needed for the DB from your repo.

No need to run Docker on your machine for deployment; only for local backend + DB if you want.
