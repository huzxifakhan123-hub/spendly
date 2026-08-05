# Spec: Add Expense

## Overview
Step 7 replaces the `/expenses/add` placeholder with a real feature that lets a logged-in user record a new expense. The user fills in an amount, category, date, and optional description; on submit the expense is inserted into the existing `expenses` table for their account and they're returned to `/profile`, where the new expense immediately shows up in the summary stats, transaction history, and category breakdown built in Steps 5 and 6.

## Depends on
- Step 1 — Database setup (`expenses` table with `user_id`, `amount`, `category`, `date`, `description` columns exists)
- Step 3 — Login and logout (`login_required` decorator and `session["user_id"]` are available)
- Step 5 — Backend routes for profile page (`/profile` reads from the `expenses` table and will reflect the new row)

## Routes
- `GET /expenses/add` — renders the add-expense form — logged-in
- `POST /expenses/add` — validates the submission and inserts a new expense row for the current user, then redirects to `/profile` — logged-in

## Database changes
No database changes. The existing `expenses` table (`user_id`, `amount`, `category`, `date`, `description`) already has every column this feature needs.

## Templates
- **Create:** `templates/add_expense.html`
  - Form fields: `amount` (number input, min `0.01`, step `0.01`), `category` (`<select>` populated from `CATEGORIES`), `date` (date input, defaults to today), `description` (optional text input)
  - Shows flashed validation errors the same way `register.html`/`login.html` do
  - Extends `base.html`
- **Modify:** `templates/profile.html`
  - Add an "+ Add expense" link/button (e.g. next to the "Recent transactions" panel title) pointing to `{{ url_for('add_expense') }}`

## Files to change
- `app.py`:
  - `add_expense()` view: change `@app.route("/expenses/add")` to `methods=["GET", "POST"]`
  - On `GET`, render `add_expense.html` with `categories=CATEGORIES` and today's date as the default
  - On `POST`, read `amount`, `category`, `date`, `description` from `request.form`, validate them, and:
    - on success: call the new `create_expense(...)` helper, flash a success message, redirect to `url_for('profile')`
    - on failure: flash an error message and re-render `add_expense.html`, preserving the submitted values
- `database/db.py`:
  - Add `create_expense(user_id, amount, category, date, description)` — parameterised `INSERT INTO expenses (...)`, following the same `get_db()` / try-finally-close pattern as `create_user`
- `templates/profile.html` — add the "+ Add expense" link described above

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (unrelated to this step, no changes)
- Use CSS variables — never hardcode hex values; any new form/button styling goes in `static/css/style.css` using existing custom properties and existing classes (`form-group`, `form-input`, `btn-submit`) where they fit
- All templates extend `base.html`
- Validate on the server regardless of client-side `input` constraints:
  - `amount` must parse as a number and be strictly greater than `0`; otherwise reject with an error and no insert
  - `category` must be one of `CATEGORIES`; otherwise reject with an error and no insert
  - `date` must parse as `YYYY-MM-DD`; otherwise reject with an error and no insert
  - `description` is optional — an empty value is stored as an empty string/`NULL`, never rejected
- A rejected submission must not insert any row and must redisplay the form with the user's previously entered values still filled in

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with all 7 categories in the dropdown and the date field defaulted to today
- [ ] Submitting valid data inserts a new row into `expenses` for the logged-in user and redirects to `/profile` with a success flash message
- [ ] The newly added expense is immediately visible on `/profile` in the transaction list, category breakdown, and summary stats
- [ ] Submitting with an empty, zero, negative, or non-numeric `amount` shows an error, inserts no row, and redisplays the form
- [ ] Submitting with a `category` not in `CATEGORIES` shows an error, inserts no row, and redisplays the form
- [ ] Submitting with a missing or malformed `date` shows an error, inserts no row, and redisplays the form
- [ ] Submitting with no `description` still successfully creates the expense
