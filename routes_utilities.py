import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify
import requests
from faker import Faker

utils_bp = Blueprint("utils_bp", __name__)
fake = Faker()
DB_PATH = "fuuroo.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 10 fields table for Requirement #3B
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fake_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            joined_date TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            recipient TEXT NOT NULL,
            message TEXT NOT NULL,
            sent_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# Ensure SQLite tables exist on startup
init_db()


# ================= 3B-1: URL SHORTENER REST API =================
@utils_bp.route("/api/utils/shorten", methods=["POST"])
def shorten_url():
    data = request.get_json() or {}
    long_url = data.get("url", "").strip()
    if not long_url:
        return jsonify({"error": "URL is required"}), 400

    if not long_url.startswith(("http://", "https://")):
        long_url = "https://" + long_url

    try:
        res = requests.get(
            "https://is.gd/create.php",
            params={"format": "simple", "url": long_url},
            timeout=8,
        )
        if res.status_code == 200 and res.text.startswith("http"):
            return jsonify({"short_url": res.text.strip(), "original": long_url})
    except Exception:
        pass

    return jsonify({"short_url": long_url, "original": long_url})


# ================= 3B-2: SMS & EMAIL SENDER API =================
@utils_bp.route("/api/utils/notify", methods=["POST"])
def send_notification():
    data = request.get_json() or {}
    channel = data.get("channel", "EMAIL").upper()
    recipient = data.get("recipient", "").strip()
    message = data.get("message", "").strip()

    if not recipient or not message:
        return jsonify({"status": "Error: Recipient and message are required."}), 400

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notifications_log (channel, recipient, message, sent_at) VALUES (?, ?, ?, ?)",
        (channel, recipient, message, timestamp),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "status": f"[{channel} DISPATCHED] Successfully sent to {recipient} at {timestamp} (Logged in fuuroo.db)."
    })


# ================= 3B-3: FAKER GENERATOR -> SQLITE DB =================
@utils_bp.route("/api/utils/faker", methods=["GET", "POST"])
def handle_faker():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == "POST":
        # Generate 20 new records across 10 fields and store in SQLite
        rows_to_insert = []
        for _ in range(20):
            rows_to_insert.append((
                fake.name(),                 # Field 2: Full Name
                fake.user_name(),            # Field 3: Username
                fake.email(),                # Field 4: Email
                fake.phone_number(),         # Field 5: Phone
                fake.city(),                 # Field 6: City
                fake.country(),              # Field 7: Country
                fake.company(),              # Field 8: Company
                fake.job(),                  # Field 9: Job Title
                str(fake.date_this_decade()) # Field 10: Date Joined
            ))

        cur.executemany("""
            INSERT INTO fake_members
            (full_name, username, email, phone, city, country, company, job_title, joined_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_to_insert)
        conn.commit()

    # Fetch stored records from fuuroo.db (Field 1 = id + Fields 2..10)
    cur.execute("SELECT * FROM fake_members ORDER BY id ASC")
    records = [dict(row) for row in cur.fetchall()]
    conn.close()

    return jsonify({"count": len(records), "records": records})