# Spec: Date Filter For Profile Page

## Overview
Step 6 adds a date-range filter to the `/profile` page. Right now `/profile` always shows all-time summary stats, all-time transaction history, and an all-time category breakdown for the logged-in user. This step lets the user narrow those three sections down to a specific time window (all time, this month, last month, last 7 days, last 30 days, or a custom start/end range) via a filter control at the top of the page. The filter is expressed as query parameters on the existing `GET /profile` route so the selected range is shareable/bookmarkable and survives a page refresh.

## Depends on
- Step 1 — Database setup (`expenses` table with a `date` column exists)
- Step 4 — Profile page static UI (template layout for stats/transactions/category sections already exists)
- Step 5 — Backend connection (`/profile` is wired to real queries in `database/queries.py`)

## Routes
- `GET /profile` — modified, not new — logged-in only (existing `login_required` decorator)
  - New optional query params:
    - `range` — one of `all`, `this_month`, `last_month`, `7_days`, `30_days`, `custom` (default: `all`)
    - `start` — `YYYY-MM-DD`, only read when `range=custom`
    - `end` — `YYYY-MM-DD`, only read when `range=custom`
  - Invalid/malformed `range`, `start`, or `end` values fall back to the `all` range rather than raising an error

## Database changes
No database changes. The `expenses.date` column (already `TEXT`, `YYYY-MM-DD`) is sufficient to filter on with a `BETWEEN`/comparison clause.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter bar above the summary stats row: a set of links/buttons for the preset ranges (All time, This month, Last month, Last 7 days, Last 30 days) plus a small custom-range form (two date inputs + Apply button)
  - The currently active preset is visually marked (e.g. an `is-active` class on the selected link)
  - Custom date inputs are pre-filled with the current `start`/`end` values when `range=custom`
  - All links/forms preserve the filter in their own `href`/action so navigating elsewhere and back doesn't lose it (i.e. no other page needs to remember it — it's not stored in session)

## Files to change
- `app.py`:
  - `profile()` view: read `range`, `start`, `end` from `request.args`, resolve them to a concrete `(start_date, end_date)` pair (or `(None, None)` for `all`), pass that pair into the three query calls, and pass the resolved filter state (`selected_range`, `start`, `end`) to the template for rendering the active filter UI
  - Add a small helper (e.g. `_resolve_date_range(range_key, start, end)`) that maps a preset key to a `(start_date, end_date)` tuple using `datetime.date` arithmetic, validates custom `start`/`end` strings, and defaults to `(None, None)` on anything unparseable
- `database/queries.py`:
  - `get_summary_stats(user_id, start_date=None, end_date=None)`
  - `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)`
  - `get_category_breakdown(user_id, start_date=None, end_date=None)`
  - Each function adds an optional `AND date >= ? AND date <= ?` clause (parameterised) only when `start_date`/`end_date` are not `None`
- `templates/profile.html` — add the filter bar described above

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format dates into SQL
- Passwords hashed with werkzeug (unrelated to this step, no changes)
- Use CSS variables — never hardcode hex values; any new filter-bar styling goes in `static/css/style.css` using existing custom properties
- All templates extend `base.html`
- No inline styles — the active-filter indicator must be a CSS class (e.g. `.is-active`), not a `style` attribute
- Date parsing must guard against invalid input (non-date strings, `start` after `end`, missing values for `range=custom`) and fall back to `all` instead of raising a 500
- `top_category` must still return `"—"` and stats must still be zero/empty when the filtered range has no matching expenses
- Query helpers must build their optional date clause with placeholders (`?`), never f-strings or `.format()`

## Definition of done
- [ ] Visiting `/profile` with no query params behaves exactly as before (all-time data)
- [ ] Visiting `/profile?range=this_month` shows only expenses dated within the current calendar month
- [ ] Visiting `/profile?range=last_month` shows only expenses dated within the previous calendar month
- [ ] Visiting `/profile?range=7_days` shows only expenses from the last 7 days
- [ ] Visiting `/profile?range=30_days` shows only expenses from the last 30 days
- [ ] Visiting `/profile?range=custom&start=2026-01-01&end=2026-01-31` shows only expenses in that inclusive range
- [ ] An invalid `range`, or a `custom` range with a missing/malformed `start`/`end`, falls back to all-time data without an error page
- [ ] Summary stats, transaction list, and category breakdown all reflect the same selected range consistently
- [ ] The active filter option is visually highlighted in the filter bar
- [ ] A user/date range with zero matching expenses shows ₹0.00 total, 0 transactions, and an empty category breakdown — no errors
