# Railway Database Setup

If you see **`Table 'railway.Terms' doesn't exist`** (or similar) when using the app, your Railway MySQL database hasn’t been initialized with the schema.

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
