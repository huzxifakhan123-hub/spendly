import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import CATEGORIES, create_user, get_user_by_email, init_db, seed_db
from database.queries import get_category_breakdown, get_recent_transactions, get_summary_stats, get_user_by_id

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

with app.app_context():
    init_db()
    seed_db()

CATEGORY_BADGES = {
    category: f"category-badge-{i % 4 + 1}" for i, category in enumerate(CATEGORIES)
}


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def _initials(name):
    words = name.split()[:2]
    return "".join(word[0] for word in words).upper()


def _build_transaction_history(user_id):
    transactions = get_recent_transactions(user_id, limit=10)
    result = []
    for txn in transactions:
        date = datetime.strptime(txn["date"], "%Y-%m-%d").strftime("%d %b %Y")
        category = txn["category"]
        result.append({
            "date": date,
            "description": txn["description"],
            "category": category,
            "amount": f"₹{txn['amount']:,.2f}",
            "badge": CATEGORY_BADGES[category],
        })
    return result


def _build_summary_stats(user_id):
    data = get_summary_stats(user_id)
    total_spent = data["total_spent"]
    transaction_count = data["transaction_count"]
    top_category = data["top_category"]
    return [
        {"label": "Total spent this month", "value": f"₹{total_spent:,.2f}"},
        {"label": "Transactions", "value": str(transaction_count)},
        {"label": "Top category", "value": top_category},
    ]


def _build_category_breakdown(user_id):
    breakdown = get_category_breakdown(user_id)
    if not breakdown:
        return []

    result = []
    for item in breakdown:
        pct = max(0, min(100, item["pct"]))
        bucket = round(pct / 5) * 5
        result.append({
            "name": item["name"],
            "amount": f"₹{item['amount']:,.2f}",
            "width_class": f"bar-w-{bucket}",
        })
    return result


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        try:
            user_id = create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html")

        session.clear()
        session["user_id"] = user_id
        flash("Account created! Welcome to Spendly.", "success")
        return redirect(url_for("profile"))

    return abort(405)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_email(email) if email else None

        if not email or not password or not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        flash("Welcome back!", "success")
        return redirect(url_for("profile"))

    return abort(405)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/profile")
@login_required
def profile():
    user_id = session["user_id"]
    user_row = get_user_by_id(user_id)
    user = {
        "initials": _initials(user_row["name"]),
        "name": user_row["name"],
        "email": user_row["email"],
        "joined": user_row["member_since"],
    }

    stats = _build_summary_stats(user_id)
    transactions = _build_transaction_history(user_id)
    categories = _build_category_breakdown(user_id)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)

