"""
Tests for Step 06 — Date Filter for Profile Page.

Spec: .claude/specs/06-date-filter-profile-page.md

Covers:
- `GET /profile` optional `range` / `start` / `end` query params
- `range` in {all, this_month, last_month, 7_days, 30_days, custom} scoping
  summary stats, transaction history, and category breakdown consistently
- Fallback to all-time data (HTTP 200, never 500) for invalid/malformed input
- Auth guard on the filtered route
- Zero-result date windows
- Direct (DB-level) coverage of get_summary_stats / get_recent_transactions /
  get_category_breakdown with explicit start_date/end_date args

These tests follow the fixture conventions of tests/test_backend_connection.py
(test_db monkeypatches db.DB_PATH to an isolated tmp_path sqlite file; client
wraps app.test_client(); _insert_user/_insert_expenses are raw parameterised
SQL helpers) so this file is fully standalone and does not share state with
other test modules.
"""

import uuid
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as app_module
import database.db as db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


def _insert_user(name="Test User", email=None):
    email = email or f"user_{uuid.uuid4().hex[:8]}@example.com"
    conn = db.get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash("password123")),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _insert_expenses(rows):
    conn = db.get_db()
    try:
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _iso(d):
    return d.isoformat()


# ================================================================== #
# DB-level tests: get_summary_stats(user_id, start_date, end_date)   #
# ================================================================== #

class TestSummaryStatsDateFiltering:
    def test_filters_totals_to_inclusive_date_range(self, test_db):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 100.0, "Food", "2026-01-01", "in-range-start-boundary"),
            (user_id, 50.0, "Bills", "2026-01-15", "in-range-middle"),
            (user_id, 25.0, "Food", "2026-01-31", "in-range-end-boundary"),
            (user_id, 999.0, "Shopping", "2025-12-31", "before-range"),
            (user_id, 999.0, "Shopping", "2026-02-01", "after-range"),
        ])

        stats = get_summary_stats(user_id, start_date="2026-01-01", end_date="2026-01-31")

        assert stats["total_spent"] == 175.0, "Out-of-range expenses must not be included"
        assert stats["transaction_count"] == 3
        assert stats["top_category"] == "Food"

    def test_zero_result_range_returns_zero_and_dash(self, test_db):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 10.0, "Food", "2026-01-01", "outside"),
        ])

        stats = get_summary_stats(user_id, start_date="2026-06-01", end_date="2026-06-30")

        assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    def test_no_start_end_behaves_like_all_time(self, test_db):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 10.0, "Food", "2020-01-01", "very-old"),
            (user_id, 20.0, "Bills", "2026-01-01", "recent"),
        ])

        all_time = get_summary_stats(user_id)
        explicit_none = get_summary_stats(user_id, start_date=None, end_date=None)

        assert all_time == explicit_none == {
            "total_spent": 30.0,
            "transaction_count": 2,
            "top_category": "Bills",
        }

    def test_only_own_user_expenses_counted_within_range(self, test_db):
        user_id = _insert_user("User A")
        other_user_id = _insert_user("User B")
        _insert_expenses([
            (user_id, 40.0, "Food", "2026-01-10", "mine"),
            (other_user_id, 500.0, "Food", "2026-01-10", "not-mine"),
        ])

        stats = get_summary_stats(user_id, start_date="2026-01-01", end_date="2026-01-31")

        assert stats["total_spent"] == 40.0
        assert stats["transaction_count"] == 1


# ================================================================== #
# DB-level tests: get_recent_transactions(user_id, ..., start, end)  #
# ================================================================== #

class TestRecentTransactionsDateFiltering:
    def test_filters_and_orders_newest_first_within_range(self, test_db):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 10.0, "Food", "2026-01-05", "day5"),
            (user_id, 20.0, "Bills", "2026-01-20", "day20"),
            (user_id, 5.0, "Food", "2026-01-10", "day10"),
            (user_id, 999.0, "Shopping", "2025-12-01", "excluded-before"),
            (user_id, 999.0, "Shopping", "2026-02-01", "excluded-after"),
        ])

        result = get_recent_transactions(user_id, start_date="2026-01-01", end_date="2026-01-31")

        assert [row["description"] for row in result] == ["day20", "day10", "day5"]

    def test_zero_result_range_returns_empty_list(self, test_db):
        user_id = _insert_user()
        _insert_expenses([(user_id, 10.0, "Food", "2026-01-01", "not-in-range")])

        assert get_recent_transactions(user_id, start_date="2026-06-01", end_date="2026-06-30") == []

    def test_respects_limit_within_filtered_range(self, test_db):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 1.0, "Food", "2026-01-01", "a"),
            (user_id, 2.0, "Food", "2026-01-02", "b"),
            (user_id, 3.0, "Food", "2026-01-03", "c"),
        ])

        result = get_recent_transactions(user_id, limit=2, start_date="2026-01-01", end_date="2026-01-31")

        assert len(result) == 2
        assert [row["description"] for row in result] == ["c", "b"]


# ================================================================== #
# DB-level tests: get_category_breakdown(user_id, start, end)        #
# ================================================================== #

class TestCategoryBreakdownDateFiltering:
    def test_filters_and_recomputes_percentages_within_range(self, test_db):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 75.0, "Food", "2026-01-10", "in-range-food"),
            (user_id, 25.0, "Bills", "2026-01-15", "in-range-bills"),
            (user_id, 1000.0, "Shopping", "2026-02-01", "excluded"),
        ])

        result = get_category_breakdown(user_id, start_date="2026-01-01", end_date="2026-01-31")

        assert [row["name"] for row in result] == ["Food", "Bills"], (
            "Categories outside the range must not skew the breakdown"
        )
        assert sum(row["pct"] for row in result) == 100

    def test_zero_result_range_returns_empty_list(self, test_db):
        user_id = _insert_user()
        _insert_expenses([(user_id, 10.0, "Food", "2026-01-01", "outside")])

        assert get_category_breakdown(user_id, start_date="2026-06-01", end_date="2026-06-30") == []


# ================================================================== #
# Route-level tests: GET /profile?range=...                          #
# ================================================================== #

class TestProfileRouteAuthGuard:
    @pytest.mark.parametrize(
        "query_string",
        [
            {},
            {"range": "this_month"},
            {"range": "last_month"},
            {"range": "7_days"},
            {"range": "30_days"},
            {"range": "custom", "start": "2026-01-01", "end": "2026-01-31"},
            {"range": "bogus"},
        ],
    )
    def test_redirects_to_login_when_logged_out(self, client, query_string):
        response = client.get("/profile", query_string=query_string)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


class TestProfileNoQueryParams:
    def test_no_query_params_behaves_like_all_time(self, test_db, client):
        user_id = _insert_user("No Filter User")
        _insert_expenses([
            (user_id, 10.0, "Food", "2020-01-01", "very-old"),
            (user_id, 20.0, "Bills", "2026-01-01", "recent"),
        ])
        _login(client, user_id)

        expected = get_summary_stats(user_id)
        response = client.get("/profile")
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert f"₹{expected['total_spent']:,.2f}" in body
        assert str(expected["transaction_count"]) in body
        assert expected["top_category"] in body
        assert 'class="filter-link is-active">All time' in body


class TestProfileRangePresets:
    def test_range_this_month_scopes_all_three_sections(self, test_db, client):
        user_id = _insert_user()
        today = date.today()
        first_of_month = today.replace(day=1)
        _insert_expenses([
            (user_id, 30.0, "Food", _iso(first_of_month), "this-month-a"),
            (user_id, 20.0, "Bills", _iso(today), "this-month-b"),
        ])
        # An expense clearly in a previous month should never be counted.
        previous_month_day = (first_of_month - timedelta(days=1)).replace(day=1)
        _insert_expenses([
            (user_id, 999.0, "Shopping", _iso(previous_month_day), "last-month-only"),
        ])
        _login(client, user_id)

        expected_stats = get_summary_stats(user_id, start_date=_iso(first_of_month), end_date=_iso(today))
        response = client.get("/profile", query_string={"range": "this_month"})
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert f"₹{expected_stats['total_spent']:,.2f}" in body
        assert "last-month-only" not in body
        assert "this-month-a" in body
        assert "this-month-b" in body
        assert 'class="filter-link is-active">This month' in body

    def test_range_last_month_scopes_all_three_sections(self, test_db, client):
        user_id = _insert_user()
        today = date.today()
        first_of_this_month = today.replace(day=1)
        last_day_prev_month = first_of_this_month - timedelta(days=1)
        first_day_prev_month = last_day_prev_month.replace(day=1)

        _insert_expenses([
            (user_id, 40.0, "Food", _iso(first_day_prev_month), "prev-month-start"),
            (user_id, 60.0, "Bills", _iso(last_day_prev_month), "prev-month-end"),
            (user_id, 999.0, "Shopping", _iso(today), "this-month-excluded"),
        ])
        _login(client, user_id)

        expected_stats = get_summary_stats(
            user_id, start_date=_iso(first_day_prev_month), end_date=_iso(last_day_prev_month)
        )
        response = client.get("/profile", query_string={"range": "last_month"})
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert f"₹{expected_stats['total_spent']:,.2f}" in body
        assert "this-month-excluded" not in body
        assert "prev-month-start" in body
        assert "prev-month-end" in body
        assert 'class="filter-link is-active">Last month' in body

    def test_range_7_days_scopes_all_three_sections(self, test_db, client):
        user_id = _insert_user()
        today = date.today()
        _insert_expenses([
            (user_id, 15.0, "Food", _iso(today), "today"),
            (user_id, 15.0, "Food", _iso(today - timedelta(days=6)), "seven-days-ago-boundary"),
            (user_id, 999.0, "Shopping", _iso(today - timedelta(days=8)), "too-old"),
        ])
        _login(client, user_id)

        response = client.get("/profile", query_string={"range": "7_days"})
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "too-old" not in body
        assert "today" in body
        assert "seven-days-ago-boundary" in body
        assert 'class="filter-link is-active">Last 7 days' in body

    def test_range_30_days_scopes_all_three_sections(self, test_db, client):
        user_id = _insert_user()
        today = date.today()
        _insert_expenses([
            (user_id, 15.0, "Food", _iso(today), "today"),
            (user_id, 15.0, "Food", _iso(today - timedelta(days=29)), "thirty-days-ago-boundary"),
            (user_id, 999.0, "Shopping", _iso(today - timedelta(days=40)), "too-old"),
        ])
        _login(client, user_id)

        response = client.get("/profile", query_string={"range": "30_days"})
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "too-old" not in body
        assert "today" in body
        assert "thirty-days-ago-boundary" in body
        assert 'class="filter-link is-active">Last 30 days' in body

    def test_range_custom_valid_scopes_all_three_sections_inclusively(self, test_db, client):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 100.0, "Food", "2026-01-01", "start-boundary"),
            (user_id, 50.0, "Bills", "2026-01-15", "middle"),
            (user_id, 25.0, "Food", "2026-01-31", "end-boundary"),
            (user_id, 999.0, "Shopping", "2025-12-31", "before-range"),
            (user_id, 999.0, "Shopping", "2026-02-01", "after-range"),
        ])
        _login(client, user_id)

        response = client.get(
            "/profile", query_string={"range": "custom", "start": "2026-01-01", "end": "2026-01-31"}
        )
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "₹175.00" in body
        assert "start-boundary" in body
        assert "middle" in body
        assert "end-boundary" in body
        assert "before-range" not in body
        assert "after-range" not in body
        assert 'class="filter-custom is-active"' in body
        assert 'value="2026-01-01"' in body
        assert 'value="2026-01-31"' in body


class TestProfileInvalidFilterFallsBackToAllTime:
    @pytest.mark.parametrize(
        "query_string",
        [
            {"range": "bogus"},
            {"range": "custom", "start": "not-a-date", "end": "2026-01-31"},
            {"range": "custom", "start": "2026-01-01", "end": "also-not-a-date"},
            {"range": "custom", "start": "2026-02-01", "end": "2026-01-01"},  # start after end
            {"range": "custom", "start": "2026-01-01"},  # missing end
            {"range": "custom", "end": "2026-01-31"},  # missing start
            {"range": "custom"},  # missing both
        ],
        ids=[
            "invalid-range-key",
            "malformed-start",
            "malformed-end",
            "start-after-end",
            "missing-end",
            "missing-start",
            "missing-both",
        ],
    )
    def test_falls_back_to_all_time_without_error(self, test_db, client, query_string):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 10.0, "Food", "2020-01-01", "very-old"),
            (user_id, 20.0, "Bills", "2026-01-01", "recent"),
        ])
        _login(client, user_id)

        expected = get_summary_stats(user_id)
        response = client.get("/profile", query_string=query_string)
        body = response.get_data(as_text=True)

        assert response.status_code == 200, "Invalid filter input must never produce a 500"
        assert f"₹{expected['total_spent']:,.2f}" in body
        assert str(expected["transaction_count"]) in body
        assert "very-old" in body, "Fallback must include all-time data, not just the (invalid) filtered subset"
        assert "recent" in body
        assert 'class="filter-link is-active">All time' in body, (
            "Invalid filter input must resolve to the 'all' preset being marked active"
        )


class TestProfileZeroResultWindow:
    def test_zero_result_range_shows_zero_state_with_no_errors(self, test_db, client):
        user_id = _insert_user()
        _insert_expenses([
            (user_id, 10.0, "Food", "2026-01-01", "outside-the-filtered-window"),
        ])
        _login(client, user_id)

        response = client.get(
            "/profile", query_string={"range": "custom", "start": "2026-06-01", "end": "2026-06-30"}
        )
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "₹0.00" in body
        assert '<div class="mock-total">0</div>' in body, "Transaction count should render as 0"
        assert "—" in body, "top_category should fall back to the em-dash placeholder"
        assert "outside-the-filtered-window" not in body

    def test_zero_result_range_stats_values_are_exact(self, test_db, client):
        user_id = _insert_user()
        _insert_expenses([(user_id, 10.0, "Food", "2026-01-01", "outside")])
        _login(client, user_id)

        stats = get_summary_stats(user_id, start_date="2026-06-01", end_date="2026-06-30")
        transactions = get_recent_transactions(user_id, start_date="2026-06-01", end_date="2026-06-30")
        categories = get_category_breakdown(user_id, start_date="2026-06-01", end_date="2026-06-30")

        assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
        assert transactions == []
        assert categories == []


class TestProfileFilterBarUiState:
    def test_only_selected_preset_is_marked_active(self, test_db, client):
        user_id = _insert_user()
        _insert_expenses([(user_id, 10.0, "Food", date.today().isoformat(), "x")])
        _login(client, user_id)

        response = client.get("/profile", query_string={"range": "last_month"})
        body = response.get_data(as_text=True)

        assert 'class="filter-link is-active">Last month' in body
        assert 'class="filter-link is-active">All time' not in body
        assert 'class="filter-link is-active">This month' not in body
        assert 'class="filter-link is-active">Last 7 days' not in body
        assert 'class="filter-link is-active">Last 30 days' not in body

    def test_custom_range_prefills_start_and_end_inputs(self, test_db, client):
        user_id = _insert_user()
        _insert_expenses([(user_id, 10.0, "Food", "2026-03-15", "x")])
        _login(client, user_id)

        response = client.get(
            "/profile", query_string={"range": "custom", "start": "2026-03-01", "end": "2026-03-31"}
        )
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'name="start" value="2026-03-01"' in body
        assert 'name="end" value="2026-03-31"' in body
