import uuid
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

import app as app_module
import database.db as db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


def _insert_user(name="Test User", email="test@example.com"):
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


# ------------------------------------------------------------------ #
# get_user_by_id                                                     #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(test_db):
    user_id = _insert_user("Jane Doe", "jane@example.com")

    result = get_user_by_id(user_id)

    assert result["name"] == "Jane Doe"
    assert result["email"] == "jane@example.com"
    assert "member_since" in result


def test_get_user_by_id_missing(test_db):
    assert get_user_by_id(999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_get_summary_stats_with_expenses(test_db):
    user_id = _insert_user()
    today = date.today().isoformat()
    _insert_expenses([
        (user_id, 10.0, "Food", today, "a"),
        (user_id, 20.0, "Bills", today, "b"),
        (user_id, 5.0, "Food", today, "c"),
    ])

    stats = get_summary_stats(user_id)

    assert stats["total_spent"] == 35.0
    assert stats["transaction_count"] == 3
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(test_db):
    user_id = _insert_user()

    stats = get_summary_stats(user_id)

    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_ordered_newest_first(test_db):
    user_id = _insert_user()
    _insert_expenses([
        (user_id, 10.0, "Food", "2026-01-01", "old"),
        (user_id, 20.0, "Bills", "2026-01-03", "newest"),
        (user_id, 5.0, "Food", "2026-01-02", "middle"),
    ])

    result = get_recent_transactions(user_id)

    assert [row["description"] for row in result] == ["newest", "middle", "old"]
    assert all({"date", "description", "category", "amount"} <= row.keys() for row in result)


def test_get_recent_transactions_no_expenses(test_db):
    user_id = _insert_user()

    assert get_recent_transactions(user_id) == []


# ------------------------------------------------------------------ #
# get_category_breakdown                                              #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_ordered_with_integer_percentages(test_db):
    user_id = _insert_user()
    today = date.today().isoformat()
    _insert_expenses([
        (user_id, 75.0, "Food", today, "a"),
        (user_id, 25.0, "Bills", today, "b"),
    ])

    result = get_category_breakdown(user_id)

    assert [row["name"] for row in result] == ["Food", "Bills"]
    assert all(isinstance(row["pct"], int) for row in result)
    assert sum(row["pct"] for row in result) == 100


def test_get_category_breakdown_no_expenses(test_db):
    user_id = _insert_user()

    assert get_category_breakdown(user_id) == []


# ------------------------------------------------------------------ #
# GET /profile                                                        #
# ------------------------------------------------------------------ #

def test_profile_redirects_when_logged_out(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_shows_real_data_for_seed_user(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    expected = get_summary_stats(1)
    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert f"₹{expected['total_spent']:,.2f}" in body
    assert str(expected["transaction_count"]) in body
    assert expected["top_category"] in body


def test_profile_zero_state_for_brand_new_user(client):
    email = f"newuser_{uuid.uuid4().hex[:8]}@example.com"
    user_id = db.create_user("New User", email, "password123")

    with client.session_transaction() as sess:
        sess["user_id"] = user_id

    response = client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "New User" in body
    assert "₹0.00" in body
