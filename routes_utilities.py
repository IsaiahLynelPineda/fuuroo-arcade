import base64
import os
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage
import requests
from faker import Faker
from flask import Blueprint, request, jsonify

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

utils_bp = Blueprint("utils", __name__)
fake = Faker()
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuuroo.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fake_users (
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
        conn.commit()


init_db()


# ================= 3B-1: URL SHORTENER =================
@utils_bp.route("/api/utils/shorten", methods=["POST"])
def shorten_url():
    data = request.get_json() or {}
    long_url = data.get("url", "").strip()
    if not long_url:
        return jsonify({"error": "URL is required"}), 400

    if not long_url.startswith(("http://", "https://")):
        long_url = "https://" + long_url

    try:
        r = requests.get(
            "https://is.gd/create.php",
            params={"format": "simple", "url": long_url},
            timeout=8,
        )
        if r.status_code == 200 and r.text.startswith("http"):
            return jsonify({"short_url": r.text.strip(), "original_url": long_url})
    except Exception:
        pass

    try:
        r = requests.get(
            "https://tinyurl.com/api-create.php",
            params={"url": long_url},
            timeout=8,
        )
        if r.status_code == 200 and r.text.startswith("http"):
            return jsonify({"short_url": r.text.strip(), "original_url": long_url})
    except Exception as e:
        return jsonify({"error": f"Shortener API unreachable: {e}"}), 502

    return jsonify({"error": "Could not shorten URL"}), 502


# ================= 3B-2: REAL EMAIL (GMAIL OAUTH API / SMTP) & SMS (SEMAPHORE) =================
@utils_bp.route("/api/utils/notify", methods=["POST"])
def send_notification():
    data = request.get_json() or {}
    channel = data.get("channel", "EMAIL").strip().upper()
    recipient = data.get("recipient", "").strip()
    message = data.get("message", "").strip()

    if not recipient or not message:
        return jsonify({"status": f"Error sending {channel}: Recipient and message are required."}), 400

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if channel == "EMAIL":
        google_token = os.environ.get("GOOGLE_OAUTH_TOKEN", "").strip()
        sender_email = os.environ.get("GOOGLE_OAUTH_EMAIL", "me").strip()

        if google_token:
            try:
                msg = EmailMessage()
                msg["Subject"] = "FuuRoo Portal Notification"
                msg["From"] = sender_email
                msg["To"] = recipient
                msg.set_content(message)

                raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
                res = requests.post(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                    headers={
                        "Authorization": f"Bearer {google_token}",
                        "Content-Type": "application/json",
                    },
                    json={"raw": raw_msg},
                    timeout=12,
                )
                if res.status_code in (200, 201):
                    return jsonify({
                        "status": f"[EMAIL SENT via Institutional Gmail API @ {timestamp}] Delivered from {sender_email} to {recipient}!"
                    })
                return jsonify({"status": f"Error sending EMAIL (Gmail API): {res.text}"}), 502
            except Exception as e:
                return jsonify({"status": f"Error sending EMAIL: {e}"}), 502

        # Fallback to SMTP if signed in with local account instead of Google OAuth
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "").strip()
        smtp_pass = os.environ.get("SMTP_PASS", "").strip()
        smtp_from = os.environ.get("SMTP_FROM", smtp_user).strip()

        if not smtp_user or not smtp_pass or "your_gmail" in smtp_user:
            return jsonify({
                "status": "Error sending EMAIL: Please sign in using 'Sign in with Google (OAuth 2.0)' first so FuuRoo can send via your institutional Gmail API!"
            }), 400

        try:
            msg = EmailMessage()
            msg["Subject"] = "FuuRoo Portal Notification"
            msg["From"] = smtp_from
            msg["To"] = recipient
            msg.set_content(message)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            return jsonify({
                "status": f"[EMAIL SENT @ {timestamp}] Delivered to {recipient} via {smtp_host}!"
            })
        except Exception as e:
            return jsonify({"status": f"Error sending EMAIL: {e}"}), 502

    if channel == "SMS":
        api_key = os.environ.get("SEMAPHORE_API_KEY", "").strip()
        sender_name = os.environ.get("SEMAPHORE_SENDER_NAME", "FuuRoo").strip()

        if not api_key:
            return jsonify({
                "status": "Error sending SMS: Missing SEMAPHORE_API_KEY in .env file."
            }), 400

        try:
            res = requests.post(
                "https://api.semaphore.co/api/v4/messages",
                data={
                    "apikey": api_key,
                    "number": recipient,
                    "message": message,
                    "sendername": sender_name,
                },
                timeout=12,
            )
            payload = res.json()
            if res.status_code in (200, 201) and isinstance(payload, list) and payload:
                msg_id = payload[0].get("message_id", "OK")
                status_text = payload[0].get("status", "Queued")
                return jsonify({
                    "status": f"[SMS {status_text.upper()} @ {timestamp}] Sent to {recipient} via Semaphore (ID: {msg_id})"
                })
            return jsonify({"status": f"Error sending SMS: {payload}"}), 502
        except Exception as e:
            return jsonify({"status": f"Error sending SMS: {e}"}), 502

    return jsonify({"status": f"Unsupported channel: {channel}"}), 400


# ================= 3B-3: FAKER DATA (10 FIELDS -> 20+ RECORDS -> SQLITE) =================
@utils_bp.route("/api/utils/faker", methods=["GET", "POST"])
def handle_faker():
    init_db()
    with get_db() as conn:
        if request.method == "POST":
            rows_to_insert = [
                (
                    fake.name(),
                    fake.user_name(),
                    fake.email(),
                    fake.phone_number(),
                    fake.city(),
                    fake.country(),
                    fake.company(),
                    fake.job(),
                    str(fake.date_between(start_date="-3y", end_date="today")),
                )
                for _ in range(20)
            ]
            conn.executemany(
                """
                INSERT INTO fake_users
                (full_name, username, email, phone, city, country, company, job_title, joined_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows_to_insert,
            )
            conn.commit()

        cursor = conn.execute("SELECT * FROM fake_users ORDER BY id ASC")
        records = [dict(row) for row in cursor.fetchall()]

    return jsonify({"count": len(records), "records": records})