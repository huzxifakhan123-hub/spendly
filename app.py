import math
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import CATEGORIES, create_expense, create_user, get_user_by_email, init_db, seed_db
from database.queries import get_category_breakdown, get_recent_transactions, get_summary_stats, get_user_by_id

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

with app.app_context():
    init_db()
    seed_db()

CATEGORY_BADGES = {
    category: f"category-badge-{i % 4 + 1}" for i, category in enumerate(CATEGORIES)
}

ANALYTICS_BAR_HEIGHTS = [42, 68, 55, 90, 73, 61, 88, 50, 77, 65, 82, 59]
ANALYTICS_LINE_VALUES = [30, 45, 38, 62, 55, 70, 58, 80, 73, 88, 76, 94]

ANALYTICS_FEATURES = [
    {
        "icon": "◈",
        "label": "Spending Trends",
        "desc": "Weekly and monthly breakdowns with velocity indicators and anomaly detection.",
        "stat": "+$2,340",
        "stat_label": "avg. monthly tracked",
        "chart": True,
    },
    {
        "icon": "⬡",
        "label": "Category Breakdown",
        "desc": "Visual sunburst of where every dollar goes — groceries, rent, subscriptions, and more.",
        "stat": "14",
        "stat_label": "tracked categories",
        "chart": False,
    },
    {
        "icon": "◉",
        "label": "Budget Forecasting",
        "desc": "ML-powered projections that learn your patterns and warn before you overspend.",
        "stat": "94%",
        "stat_label": "forecast accuracy",
        "chart": True,
    },
    {
        "icon": "⬔",
        "label": "Smart Alerts",
        "desc": "Real-time push alerts when unusual charges appear or budgets hit 80%.",
        "stat": "< 3s",
        "stat_label": "alert latency",
        "chart": False,
    },
]


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


def _resolve_date_range(range_key, start_raw, end_raw):
    today = date.today()

    if range_key == "this_month":
        return today.replace(day=1).isoformat(), today.isoformat(), "this_month"

    if range_key == "last_month":
        last_day_prev = today.replace(day=1) - timedelta(days=1)
        return last_day_prev.replace(day=1).isoformat(), last_day_prev.isoformat(), "last_month"

    if range_key == "7_days":
        return (today - timedelta(days=6)).isoformat(), today.isoformat(), "7_days"

    if range_key == "30_days":
        return (today - timedelta(days=29)).isoformat(), today.isoformat(), "30_days"

    if range_key == "custom" and start_raw and end_raw:
        try:
            start = datetime.strptime(start_raw, "%Y-%m-%d").date()
            end = datetime.strptime(end_raw, "%Y-%m-%d").date()
        except ValueError:
            return None, None, "all"
        if start > end:
            return None, None, "all"
        return start.isoformat(), end.isoformat(), "custom"

    return None, None, "all"


def _build_transaction_history(user_id, start_date=None, end_date=None):
    transactions = get_recent_transactions(user_id, limit=10, start_date=start_date, end_date=end_date)
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


def _build_summary_stats(user_id, start_date=None, end_date=None):
    data = get_summary_stats(user_id, start_date=start_date, end_date=end_date)
    total_spent = data["total_spent"]
    transaction_count = data["transaction_count"]
    top_category = data["top_category"]
    return [
        {"label": "Total spent this month", "value": f"₹{total_spent:,.2f}"},
        {"label": "Transactions", "value": str(transaction_count)},
        {"label": "Top category", "value": top_category},
    ]


def _svg_line_points(values, width=280, height=80):
    count = len(values)
    points = []
    for i, value in enumerate(values):
        x = (i / (count - 1)) * width
        y = height - (value / 100) * height
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def _build_category_breakdown(user_id, start_date=None, end_date=None):
    breakdown = get_category_breakdown(user_id, start_date=start_date, end_date=end_date)
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


@app.route("/analytics")
def analytics():
    bars = [
        {"height": height, "shade": i % 3}
        for i, height in enumerate(ANALYTICS_BAR_HEIGHTS)
    ]
    return render_template(
        "analytics.html",
        bars=bars,
        line_points=_svg_line_points(ANALYTICS_LINE_VALUES),
        features=ANALYTICS_FEATURES,
        waitlist_count=1247,
    )


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

    start_date, end_date, active_range = _resolve_date_range(
        request.args.get("range", "all"),
        request.args.get("start"),
        request.args.get("end"),
    )

    stats = _build_summary_stats(user_id, start_date, end_date)
    transactions = _build_transaction_history(user_id, start_date, end_date)
    categories = _build_category_breakdown(user_id, start_date, end_date)

    filters = {
        "active": active_range,
        "start": start_date if active_range == "custom" else "",
        "end": end_date if active_range == "custom" else "",
    }

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        filters=filters,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "GET":
        form = {"amount": "", "category": "", "date": date.today().isoformat(), "description": ""}
        return render_template("add_expense.html", categories=CATEGORIES, form=form)

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    form = {"amount": amount_raw, "category": category, "date": date_raw, "description": description}

    try:
        amount = float(amount_raw)
    except ValueError:
        amount = None

    if amount is None or not math.isfinite(amount) or amount <= 0:
        flash("Enter a valid amount greater than 0.", "error")
        return render_template("add_expense.html", categories=CATEGORIES, form=form)

    if category not in CATEGORIES:
        flash("Select a valid category.", "error")
        return render_template("add_expense.html", categories=CATEGORIES, form=form)

    try:
        expense_date = datetime.strptime(date_raw, "%Y-%m-%d").date().isoformat()
    except ValueError:
        flash("Enter a valid date.", "error")
        return render_template("add_expense.html", categories=CATEGORIES, form=form)

    create_expense(session["user_id"], round(amount, 2), category, expense_date, description)
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)

