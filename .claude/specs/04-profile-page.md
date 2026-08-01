# Spec: Profile Page

## Overview
Replace the `/profile` stub with a fully designed profile page showing static, hardcoded data. The goal is to establish the complete UI layout — user info card, summary stats, transaction history table, and category breakdown — before any real database queries are wired up in a later step. Building the UI first lets the design be validated in isolation and ensures the template is ready for the backend-connection step that follows.

## Depends on
- Step 01 — Database setup (`users` and `expenses` tables must exist)
- Step 02 — Registration (user accounts must be creatable)
- Step 03 — Login and Logout (session must be set; `login_required` decorator must exist; `/profile` must be a protected route)

## Routes
- `GET /profile` — render the profile page — logged-in only (use the existing `login_required` decorator; redirect to `/login` if not authenticated)

## Database changes
No database changes. The existing `users` and `expenses` tables are sufficient. No DB queries are made in this step — all data is hardcoded in `app.py`.

## Templates
- **Create:** `templates/profile.html` — full profile page extending `base.html`; contains four sections:
  1. **User info card** — avatar initials, name, email, member-since date (all hardcoded)
  2. **Summary stats row** — total spent, number of transactions, top category (hardcoded)
  3. **Transaction history table** — list of recent expenses with date, description, category badge, amount (hardcoded rows)
  4. **Category breakdown** — per-category totals displayed as a list with progress-bar rows (hardcoded)
- **Modify:** `templates/base.html` — show the logged-in user's name in the navbar next to the Logout link (requires `session["user_name"]` to be set at login)

## Files to change
- `app.py`:
  - Replace the `/profile` stub with a real view function decorated with `login_required` that passes hardcoded context variables (`user`, `stats`, `transactions`, `categories`) to `profile.html`
  - In `login()`, additionally store `session["user_name"] = user["name"]` on successful login (reuses the already-fetched user row — no extra DB query)
- `templates/base.html` — update the navbar to display `session.user_name` alongside the Logout link when logged in

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` if any DB call is ever needed
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values; add any new colors (e.g. category badge colors) as new custom properties in the `:root` block of `static/css/style.css`
- All templates extend `base.html`
- No inline styles — including dynamic values like progress-bar widths; use small pre-defined width classes (e.g. `.pct-10`, `.pct-20`, ... in steps of 5) instead of a `style="width: …"` attribute
- Authentication guard: use the existing `login_required` decorator from `app.py`
- All data passed to the template must be hardcoded Python dicts/lists in `app.py` — no DB queries in this step
- Category badges must use a CSS class per category (e.g. `.badge-food`, `.badge-transport`), not inline colour styles

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The page displays a user info card with a name and email
- [ ] The page displays at least three summary stat values (e.g. total spent, transaction count, top category)
- [ ] The page displays a transaction history table with at least three hardcoded rows
- [ ] The page displays a category breakdown section with at least three categories
- [ ] The navbar shows the logged-in state (username + logout link) on every page, not just `/profile`
- [ ] No hex colour values appear in `profile.html` — only CSS variables

