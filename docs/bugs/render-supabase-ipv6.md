# Bug: Render cannot reach Supabase — "Network is unreachable" (IPv6)

**Date discovered:** 2026-04-23  
**Environment:** Render (free tier) → Supabase PostgreSQL  
**Status:** Resolved

---

## Symptom

After switching `DATABASE_URL` from Railway MySQL to Supabase and deploying to Render, every request that touched the database failed. The Render logs showed:

```
psycopg2.OperationalError: connection to server at "db.skuawzbdtmagluezoqae.supabase.co"
(2600:1f13:838:6e5a:c220:9f0d:2e41:9314), port 5432 failed: Network is unreachable
    Is the server running on that host and accepting TCP/IP connections?
```

Affected endpoints from the logs: `/api/maintenance`, `/api/settings`, `/api/auth/google`.

---

## How we ruled out a code bug

The traceback ends at `psycopg2.connect(url)` — meaning the connection string was parsed correctly and Python got as far as opening a TCP socket. The failure happens at the network layer before any SQL is executed or any authentication is attempted.

The key clue is the IP address in the error: `2600:1f13:838:6e5a:c220:9f0d:2e41:9314`. That is an IPv6 address. Render's free tier does not support outbound IPv6 connections. Supabase's direct connection host (`db.[ref].supabase.co`) resolves to an IPv6 address in some regions, so the socket open fails immediately with "Network is unreachable."

If it had been a code bug — wrong credentials, bad SQL, schema mismatch — the connection would have succeeded first and the error would have come from psycopg2 or SQLAlchemy at a later stage (e.g. `OperationalError: password authentication failed` or `ProgrammingError: relation does not exist`).

---

## Root cause

Render free tier → no outbound IPv6. Supabase direct URL → resolves to IPv6 in some regions. These two facts combine to make the direct connection URL unusable on Render's free tier.

---

## Fix

Use Supabase's **Session pooler** URL instead of the direct connection URL. The pooler resolves to an IPv4 address that Render can reach.

**Where to get it:** Supabase Dashboard → Project Settings → Database → Connection string → set Mode to **Session** → copy the URI.

The pooler URL has a different host and username format:
```
postgresql://postgres.YOURREF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
```

vs. the direct URL that fails:
```
postgresql://postgres:PASSWORD@db.YOURREF.supabase.co:5432/postgres
```

Update `DATABASE_URL` on Render to the pooler URL and redeploy.

**Why Session mode and not Transaction mode?** Transaction mode (port 6543) doesn't support prepared statements. SQLAlchemy uses prepared statements by default, causing failures. Session mode gives each connection a dedicated slot with full PostgreSQL feature support.
