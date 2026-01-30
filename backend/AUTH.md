# Auth (client login and security setup)

Minimal auth for the client side: one dev client can log in, complete a one-time security setup, then use the app. Admin view and other users are planned later.

## Dev client

- Username: `syllabify-client`
- Password: `ineedtocutmytoenails422`

Used so developers can log in and test. The same account is the client; admin dashboard and role separation come later.

## Flow

1. POST `/api/auth/login` with `{ "username": "syllabify-client", "password": "..." }`. Returns `{ "token", "username", "security_setup_done" }`.
2. If `security_setup_done` is false, frontend sends user to security-setup page. User submits security questions and answers. POST `/api/auth/security-setup` with `Authorization: Bearer <token>` and body `{ "questions": [ { "question": "...", "answer": "..." } ] }`. Backend stores hashed answers and sets `security_setup_done` on the user. One-time only.
3. GET `/api/auth/me` with `Authorization: Bearer <token>` returns `{ "username", "security_setup_done" }` for protected routes.

## Database

- `Users`: `password_hash`, `security_setup_done` (see `docker/init.sql`). Dev client is created on first successful login if missing.
- `UserSecurityAnswers`: `user_id`, `question_text`, `answer_hash`. Used only for security Q&A; no recovery flow implemented yet.

## Existing databases

If MySQL was created before these columns existed, run:

```sql
ALTER TABLE Users ADD COLUMN password_hash VARCHAR(255), ADD COLUMN security_setup_done BOOLEAN DEFAULT FALSE;
```

Then ensure `UserSecurityAnswers` exists (same as in `docker/init.sql`).
