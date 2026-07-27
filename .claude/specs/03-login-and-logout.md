# Spec: Login and Logout

## Overview
Implement session-based authentication so registered users can sign in and out of Spendly. This step upgrades the existing stub `GET /login` route into a full form handler that verifies credentials against the `users` table and starts a Flask session, and replaces the placeholder `GET /logout` route with real session teardown. This is the step that turns Spendly from a public marketing site into an app with an authenticated area — every future step (profile, expenses) depends on the session mechanism introduced here.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`)
- Step 02 — Registration (users must be able to register before they can log in)

## Routes
- `GET /login` — render login form — public (already exists as stub, upgrade it). If already logged in, redirect to `/`
- `POST /login` — verify credentials, start session, redirect to `/` — public
- `GET /logout` — clear session, redirect to `/login` — logged-in
- `GET /register` — if already logged in, redirect to `/` (existing route, guard added)

## Database changes
No new tables or columns. The existing `users` table (id, name, email, password_hash, created_at) covers all requirements.

A new DB helper must be added to `database/db.py`:
- `get_user_by_email(email)` — returns the matching row from `users` (as a `sqlite3.Row`) or `None` if no match.

## Templates
- **Modify**: `templates/login.html`
  - Change the form `action` from the hardcoded `/login` to `url_for('login')`
  - Replace the custom `{% if error %}` block with `get_flashed_messages(with_categories=true)`, matching the pattern already used in `templates/register.html`
  - Keep all existing visual design

No new templates.

## Files to change
- `app.py`:
  - Upgrade `login()` to handle `GET` and `POST`
  - On `POST`: look up the user by email, verify the password with `check_password_hash`, and on success store `user_id` in `session` and redirect to `url_for('landing')`
  - On invalid credentials: flash an error and re-render the form — do not reveal whether the email or the password was wrong
  - Implement `logout()`: clear the session and redirect to `url_for('login')` with a flashed confirmation message
  - Add a `login_required` decorator that checks `session.get('user_id')`; redirect to `url_for('login')` with a flash message if absent. Apply it to `logout()`. This decorator is the mechanism future steps (profile, expenses) will reuse to protect their routes.
- `database/db.py` — add `get_user_by_email()` helper
- `templates/login.html` — wire up form action and flash message display

## Files to create
None.

## New dependencies
No new dependencies. Uses `werkzeug.security` (already installed for hashing) and Flask's built-in `session` / `flash` / `redirect` / `url_for`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings or string formatting in SQL
- Passwords hashed with werkzeug — verify with `werkzeug.security.check_password_hash`, never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode URLs (this fixes the existing hardcoded `/login` in `login.html`)
- Server-side validation on `POST /login`:
  1. Both `email` and `password` are non-empty
  2. Email exists in `users`
  3. Password hash matches
- On any validation failure, flash a single generic error (e.g. "Invalid email or password") and re-render the form — do not redirect, do not leak which field was wrong
- On success, store only `user_id` in the session (no password or hash)
- `logout()` must fully clear the session (`session.clear()`), not just remove `user_id`
- Use `abort(405)` if an unsupported HTTP method reaches `/login`

## Definition of done
- [ ] `GET /login` renders the login form without errors
- [ ] Submitting valid credentials (e.g. `demo@spendly.com` / `demo123`) redirects to `/` and starts a session
- [ ] Submitting an unregistered email re-renders the form with a generic invalid-credentials error, no session started
- [ ] Submitting a registered email with the wrong password re-renders the form with the same generic error, no session started
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/login`
- [ ] Visiting `/logout` while logged out redirects to `/login` via `login_required` rather than erroring
- [ ] After logout, the session no longer contains `user_id` (verifiable via browser dev tools/cookies)
- [ ] No plaintext password is ever compared or logged
