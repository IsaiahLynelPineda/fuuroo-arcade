import hashlib
import os
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage
from flask import Blueprint, request, jsonify, redirect, url_for
import requests
from faker import Faker

utils_bp = Blueprint("utils_bp", __name__)
fake = Faker()
DB_PATH = "fuuroo.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS short_urls (
            code TEXT PRIMARY KEY,
            long_url TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


def send_real_email(recipient: str, message: str):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    smtp_from = os.getenv("SMTP_FROM", smtp_user).strip()

    if not smtp_user or not smtp_pass:
        raise RuntimeError("Missing SMTP_USER or SMTP_PASS environment variables.")

    msg = EmailMessage()
    msg["Subject"] = "FuuRoo Portal Notification"
    msg["From"] = smtp_from
    msg["To"] = recipient
    msg.set_content(message)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def send_real_sms(recipient: str, message: str):
    semaphore_key = os.getenv("SEMAPHORE_API_KEY", "").strip()
    if semaphore_key:
        sender_name = os.getenv("SEMAPHORE_SENDER_NAME", "FuuRoo").strip()
        res = requests.post(
            "https://api.semaphore.co/api/v4/messages",
            data={
                "apikey": semaphore_key,
                "number": recipient,
                "message": message,
                "sendername": sender_name,
            },
            timeout=15,
        )
        res.raise_for_status()
        return

    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    if account_sid and auth_token and from_number:
        res = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            data={
                "From": from_number,
                "To": recipient,
                "Body": message,
            },
            auth=(account_sid, auth_token),
            timeout=15,
        )
        res.raise_for_status()
        return

    raise RuntimeError("Missing SMS gateway credentials (set SEMAPHORE_API_KEY or Twilio variables).")


# ================= 3B-1: URL SHORTENER REST API =================
@utils_bp.route("/api/utils/shorten", methods=["POST"])
def shorten_url():
    data = request.get_json(silent=True) or {}
    long_url = (data.get("url") or "").strip()
    if not long_url:
        return jsonify({"error": "URL is required"}), 400

    if not long_url.startswith(("http://", "https://")):
        long_url = "https://" + long_url

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(
            "https://is.gd/create.php",
            params={"format": "simple", "url": long_url},
            headers=headers,
            timeout=6,
        )
        short_link = res.text.strip()
        if res.status_code == 200 and short_link.startswith(("http://", "https://")):
            return jsonify({"short_url": short_link, "original": long_url, "provider": "is.gd"})
    except Exception:
        pass

    try:
        res = requests.get(
            "https://tinyurl.com/api-create.php",
            params={"url": long_url},
            headers=headers,
            timeout=6,
        )
        short_link = res.text.strip()
        if res.status_code == 200 and short_link.startswith(("http://", "https://")):
            return jsonify({"short_url": short_link, "original": long_url, "provider": "tinyurl"})
    except Exception:
        pass

    try:
        res = requests.post(
            "https://cleanuri.com/api/v1/shorten",
            data={"url": long_url},
            headers=headers,
            timeout=6,
        )
        short_link = (res.json() or {}).get("result_url", "").strip()
        if res.status_code == 200 and short_link.startswith(("http://", "https://")):
            return jsonify({"short_url": short_link, "original": long_url, "provider": "cleanuri"})
    except Exception:
        pass

    code = hashlib.sha256(long_url.encode("utf-8")).hexdigest()[:6]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO short_urls (code, long_url, created_at) VALUES (?, ?, ?)",
        (code, long_url, timestamp),
    )
    conn.commit()
    conn.close()

    short_url = url_for("utils_bp.redirect_short_url", code=code, _external=True)
    return jsonify({"short_url": short_url, "original": long_url, "provider": "local-fallback"})


@utils_bp.route("/s/<code>")
def redirect_short_url(code):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT long_url FROM short_urls WHERE code = ?", (code,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "Short URL not found", 404
    return redirect(row["long_url"])


# ================= 3B-2: SMS & EMAIL SENDER API =================
@utils_bp.route("/api/utils/notify", methods=["POST"])
def send_notification():
    data = request.get_json(silent=True) or {}
    channel = (data.get("channel") or "EMAIL").upper().strip()
    recipient = (data.get("recipient") or "").strip()
    message = (data.get("message") or "").strip()

    if not recipient or not message:
        return jsonify({"status": "Error: Recipient and message are required."}), 400

    try:
        if channel == "EMAIL":
            send_real_email(recipient, message)
        elif channel == "SMS":
            send_real_sms(recipient, message)
        else:
            return jsonify({"status": f"Error: Unsupported channel '{channel}'."}), 400
    except Exception as exc:
        return jsonify({"status": f"Error sending {channel}: {exc}"}), 500

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
        "status": f"[{channel} SENT] Delivered to {recipient} at {timestamp} (Logged in fuuroo.db)."
    })


# ================= 3B-3: FAKER GENERATOR -> SQLITE DB =================
@utils_bp.route("/api/utils/faker", methods=["GET", "POST"])
def handle_faker():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == "POST":
        rows_to_insert = []
        for _ in range(20):
            rows_to_insert.append((
                fake.name(),
                fake.user_name(),
                fake.email(),
                fake.phone_number(),
                fake.city(),
                fake.country(),
                fake.company(),
                fake.job(),
                str(fake.date_this_decade()),
            ))

        cur.executemany("""
            INSERT INTO fake_members
            (full_name, username, email, phone, city, country, company, job_title, joined_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_to_insert)
        conn.commit()

    cur.execute("SELECT * FROM fake_members ORDER BY id ASC")
    records = [dict(row) for row in cur.fetchall()]
    conn.close()

    return jsonify({"count": len(records), "records": records})