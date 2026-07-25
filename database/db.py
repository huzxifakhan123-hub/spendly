import os
import sqlite3
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db")

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()

    existing = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
    if existing["count"] > 0:
        conn.close()
        return

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cursor.lastrowid

    today = date.today()
    sample_expenses = [
        (user_id, 12.50, "Food", (today.replace(day=1) + timedelta(days=1)).isoformat(), "Groceries"),
        (user_id, 45.00, "Transport", (today.replace(day=1) + timedelta(days=3)).isoformat(), "Fuel"),
        (user_id, 89.99, "Bills", (today.replace(day=1) + timedelta(days=5)).isoformat(), "Electricity bill"),
        (user_id, 30.00, "Health", (today.replace(day=1) + timedelta(days=7)).isoformat(), "Pharmacy"),
        (user_id, 15.00, "Entertainment", (today.replace(day=1) + timedelta(days=9)).isoformat(), "Movie tickets"),
        (user_id, 60.00, "Shopping", (today.replace(day=1) + timedelta(days=11)).isoformat(), "Clothes"),
        (user_id, 20.00, "Other", (today.replace(day=1) + timedelta(days=13)).isoformat(), "Miscellaneous"),
        (user_id, 8.75, "Food", (today.replace(day=1) + timedelta(days=15)).isoformat(), "Coffee"),
    ]

    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        sample_expenses,
    )

    conn.commit()
    conn.close()
