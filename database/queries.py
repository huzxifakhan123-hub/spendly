from datetime import datetime

from database.db import get_db


def _user_date_filter(user_id, start_date, end_date):
    if start_date and end_date:
        return "user_id = ? AND date >= ? AND date <= ?", (user_id, start_date, end_date)
    return "user_id = ?", (user_id,)


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created.strftime("%B %Y"),
    }


def get_summary_stats(user_id, start_date=None, end_date=None):
    where, params = _user_date_filter(user_id, start_date, end_date)
    conn = get_db()
    try:
        totals = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM expenses WHERE {where}",
            params,
        ).fetchone()
        top = conn.execute(
            f"""
            SELECT category, SUM(amount) AS total
            FROM expenses
            WHERE {where}
            GROUP BY category
            ORDER BY total DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": round(totals["total"], 2),
        "transaction_count": totals["count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    where, params = _user_date_filter(user_id, start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            f"""
            SELECT date, description, category, amount
            FROM expenses
            WHERE {where}
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


def get_category_breakdown(user_id, start_date=None, end_date=None):
    where, params = _user_date_filter(user_id, start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            f"""
            SELECT category, SUM(amount) AS amount
            FROM expenses
            WHERE {where}
            GROUP BY category
            ORDER BY amount DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    total = sum(row["amount"] for row in rows)
    breakdown = [
        {"name": row["category"], "amount": row["amount"], "pct": round(row["amount"] / total * 100)}
        for row in rows
    ]

    remainder = 100 - sum(item["pct"] for item in breakdown)
    breakdown[0]["pct"] += remainder

    return breakdown
