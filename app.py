import sqlite3
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

with app.app_context():
    init_db()
    seed_db()


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
    user = {
        "initials": "DU",
        "name": "Demo User",
        "email": "demo@spendly.com",
        "joined": "January 2026",
    }

    stats = [
        {"label": "Total spent this month", "value": "₹18,420"},
        {"label": "Transactions", "value": "24"},
        {"label": "Top category", "value": "Bills"},
    ]

    transactions = [
        {"date": "26 Jul 2026", "description": "Groceries run", "category": "Food", "amount": "₹1,240", "badge": "category-badge-2"},
        {"date": "24 Jul 2026", "description": "Fuel top-up", "category": "Transport", "amount": "₹2,000", "badge": "category-badge-3"},
        {"date": "22 Jul 2026", "description": "Electricity bill", "category": "Bills", "amount": "₹3,150", "badge": "category-badge-1"},
        {"date": "20 Jul 2026", "description": "Movie night", "category": "Entertainment", "amount": "₹850", "badge": "category-badge-4"},
        {"date": "18 Jul 2026", "description": "Pharmacy", "category": "Health", "amount": "₹640", "badge": "category-badge-2"},
    ]

    categories = [
        {"name": "Bills", "amount": "₹6,200", "bar_class": "", "width_class": "bar-w-100"},
        {"name": "Food", "amount": "₹4,850", "bar_class": "mock-bar-2", "width_class": "bar-w-80"},
        {"name": "Shopping", "amount": "₹3,100", "bar_class": "mock-bar-3", "width_class": "bar-w-50"},
        {"name": "Transport", "amount": "₹2,400", "bar_class": "mock-bar-4", "width_class": "bar-w-40"},
    ]

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

