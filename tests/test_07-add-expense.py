import uuid
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

import app as app_module
import database.db as db


# ------------------------------------------------------------------ #
# Fixtures — mirrors tests/test_backend_connection.py conventions     #
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
    email = email or f"{uuid.uuid4().hex[:8]}@example.com"
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


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _get_expenses(user_id):
    conn = db.get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchall()
    finally:
        conn.close()


def _count_expenses(user_id):
    return len(_get_expenses(user_id))


VALID_PAYLOAD = {
    "amount": "42.50",
    "category": "Food",
    "date": "2026-01-15",
    "description": "Groceries",
}


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

def test_get_add_expense_redirects_when_logged_out(test_db, client):
    response = client.get("/expenses/add")

    assert response.status_code == 302, "GET /expenses/add while logged out should redirect"
    assert "/login" in response.headers["Location"], "Should redirect to /login"


def test_post_add_expense_redirects_when_logged_out(test_db, client):
    response = client.post("/expenses/add", data=VALID_PAYLOAD)

    assert response.status_code == 302, "POST /expenses/add while logged out should redirect"
    assert "/login" in response.headers["Location"], "Should redirect to /login"


# ------------------------------------------------------------------ #
# GET — form rendering                                                #
# ------------------------------------------------------------------ #

def test_get_add_expense_shows_form_with_all_categories_and_todays_date(test_db, client):
    user_id = _insert_user()
    _login(client, user_id)

    response = client.get("/expenses/add")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert len(db.CATEGORIES) == 7, "Spec expects exactly 7 categories to exist"
    for category in db.CATEGORIES:
        assert f'value="{category}"' in body, f"Expected category '{category}' in dropdown"

    today = date.today().isoformat()
    assert f'value="{today}"' in body, "Date field should default to today's date"
    assert "amount" in body and "category" in body and "description" in body


# ------------------------------------------------------------------ #
# POST — happy path / DB side effects                                 #
# ------------------------------------------------------------------ #

def test_post_valid_data_inserts_expense_and_redirects_to_profile(test_db, client):
    user_id = _insert_user()
    _login(client, user_id)

    response = client.post("/expenses/add", data=VALID_PAYLOAD)

    assert response.status_code == 302, "Valid submission should redirect"
    assert response.headers["Location"].endswith("/profile"), "Should redirect to /profile"

    rows = _get_expenses(user_id)
    assert len(rows) == 1, "Exactly one expense row should be inserted"
    row = rows[0]
    assert row["user_id"] == user_id
    assert row["amount"] == pytest.approx(42.50)
    assert row["category"] == "Food"
    assert row["date"] == "2026-01-15"
    assert row["description"] == "Groceries"


def test_post_valid_data_flashes_success_message(test_db, client):
    user_id = _insert_user()
    _login(client, user_id)

    response = client.post("/expenses/add", data=VALID_PAYLOAD, follow_redirects=True)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "added" in body.lower(), "Expected a success flash message mentioning the expense was added"


def test_post_valid_data_does_not_leak_into_other_users_expenses(test_db, client):
    user_id = _insert_user("Owner", "owner@example.com")
    other_user_id = _insert_user("Other", "other@example.com")
    _login(client, user_id)

    client.post("/expenses/add", data=VALID_PAYLOAD)

    assert _count_expenses(user_id) == 1
    assert _count_expenses(other_user_id) == 0, "Expense must be attributed to the logged-in user only"


# ------------------------------------------------------------------ #
# POST — amount validation                                            #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("bad_amount", ["", "0", "-5", "-0.01", "abc", "NaN"])
def test_post_invalid_amount_rejected_no_row_inserted(test_db, client, bad_amount):
    user_id = _insert_user()
    _login(client, user_id)

    payload = dict(VALID_PAYLOAD, amount=bad_amount)
    response = client.post("/expenses/add", data=payload)
    body = response.get_data(as_text=True)

    assert response.status_code == 200, "Invalid submission should redisplay the form, not redirect"
    assert _count_expenses(user_id) == 0, f"No row should be inserted for amount={bad_amount!r}"
    assert "amount" in body.lower() or "valid" in body.lower(), "Expected a validation error about the amount"


def test_post_invalid_amount_redisplays_submitted_values(test_db, client):
    user_id = _insert_user()
    _login(client, user_id)

    payload = dict(VALID_PAYLOAD, amount="-5")
    response = client.post("/expenses/add", data=payload)
    body = response.get_data(as_text=True)

    assert "-5" in body, "Previously entered amount should still be filled in on redisplay"
    assert "Groceries" in body, "Previously entered description should still be filled in on redisplay"


# ------------------------------------------------------------------ #
# POST — category validation                                         #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("bad_category", ["", "Vacation", "food", "Groceries"])
def test_post_invalid_category_rejected_no_row_inserted(test_db, client, bad_category):
    user_id = _insert_user()
    _login(client, user_id)

    payload = dict(VALID_PAYLOAD, category=bad_category)
    response = client.post("/expenses/add", data=payload)

    assert response.status_code == 200
    assert _count_expenses(user_id) == 0, f"No row should be inserted for category={bad_category!r}"


# ------------------------------------------------------------------ #
# POST — date validation                                              #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("bad_date", ["", "not-a-date", "15/01/2026", "2026-13-40", "2026/01/15"])
def test_post_invalid_date_rejected_no_row_inserted(test_db, client, bad_date):
    user_id = _insert_user()
    _login(client, user_id)

    payload = dict(VALID_PAYLOAD, date=bad_date)
    response = client.post("/expenses/add", data=payload)

    assert response.status_code == 200
    assert _count_expenses(user_id) == 0, f"No row should be inserted for date={bad_date!r}"


def test_post_missing_date_field_rejected_no_row_inserted(test_db, client):
    user_id = _insert_user()
    _login(client, user_id)

    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "date"}
    response = client.post("/expenses/add", data=payload)

    assert response.status_code == 200
    assert _count_expenses(user_id) == 0, "No row should be inserted when the date field is entirely missing"


# ------------------------------------------------------------------ #
# POST — optional description                                        #
# ------------------------------------------------------------------ #

def test_post_no_description_still_creates_expense(test_db, client):
    user_id = _insert_user()
    _login(client, user_id)

    payload = dict(VALID_PAYLOAD)
    payload["description"] = ""
    response = client.post("/expenses/add", data=payload)

    assert response.status_code == 302, "Missing description should not block a valid submission"
    assert response.headers["Location"].endswith("/profile")

    rows = _get_expenses(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] in ("", None), "Empty description should be stored, not rejected"


def test_post_description_field_entirely_absent_still_creates_expense(test_db, client):
    user_id = _insert_user()
    _login(client, user_id)

    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "description"}
    response = client.post("/expenses/add", data=payload)

    assert response.status_code == 302, "Omitting description entirely should still succeed"
    assert _count_expenses(user_id) == 1
