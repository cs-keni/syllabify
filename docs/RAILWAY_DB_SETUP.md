# Railway Database Setup

If you see **`Table 'railway.Terms' doesn't exist`** (or similar) when using the app, your Railway MySQL database hasn’t been initialized with the schema.

If you see **"Failed to fetch courses"** or **"Failed to save assignments"** and Render logs show **`Unknown column 'a.course_id'`** or **`Unknown column 'start_date'`**, the `Assignments` table was created from an older schema. Apply the fix in **§1b** below.

**Private vs public:** Use **public network** for both schema and Render. Private only works for services in the same Railway project; your backend is on Render, so use public.

## 1. Apply the schema

1. In **Railway** → your project → open your **MySQL** service.
2. Open the **Connect** tab and copy the connection details (host, port, user, password).
3. From your machine, run the schema script against that database:

   ```bash
   mysql -h shinkansen.proxy.rlwy.net -u root -p --port 13083 --protocol=TCP railway < docker/railway-schema.sql
   ```

   Or use a GUI (MySQL Workbench, DBeaver, TablePlus, etc.):
   - Connect with the Railway credentials
   - Open `docker/railway-schema.sql`
   - Execute it

   Or in Railway’s **Query** tab (if available): paste and run the contents of `docker/railway-schema.sql`.

### 1b. Fix Assignments table (if you see “Unknown column” errors)

If the `Assignments` table already existed when you ran the schema (so it wasn’t recreated) and you get **Unknown column 'a.course_id'** or **Unknown column 'start_date'** in Render:

1. In MySQL Workbench, connect to Railway and select the `railway` database.
2. Open **File → Open SQL Script** and choose `docker/railway-migration-fix-assignments.sql`.
3. Run each statement in the script (e.g. one block at a time). If you get **Duplicate column** or **Duplicate key**, skip that statement.
4. Redeploy or retry the app; courses list and saving assignments should work.

## 2. Create a term

After the schema is applied, you must have at least one term before confirming a syllabus:

- Sign in to your app.
- Go to the **Dashboard** and create a term (e.g. “Spring 2025”, Jan 13–May 5).
- Make sure this term is set as the active term.

Syllabus confirmation will fail with “No term found” if there are no terms.

## 3. Check backend env vars

Your Render backend must point at the Railway MySQL instance. In Render → backend service → Environment:

- `DB_HOST` = `shinkansen.proxy.rlwy.net`
- `DB_PORT` = `13083`
- `DB_NAME` = `railway`
- `DB_USER` = `root`
- `DB_PASSWORD` = *(your Railway MySQL password)*
