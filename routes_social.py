import os
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, request
import requests

social_bp = Blueprint("social_bp", __name__)
DB_PATH = "fuuroo.db"


def init_social_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS social_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            handle TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            external_status TEXT NOT NULL,
            posted_at TEXT NOT NULL
        )
    """)

    cur.execute("SELECT COUNT(*) FROM social_posts")
    if cur.fetchone()[0] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        seed_posts = [
            ("IG", "@fuuroo", "Retro gaming setup & classic movie night on FuuRoo.com! #Web2 #Throwback", "", "Seeded", now),
            ("X", "@FuuRooWeb", "Status Update: Added Ben 10, GunBlood & Whack Your Boss to FuuRoo!", "", "Seeded", now),
            ("FB", "/FuuRoo", "FuuRoo.com shared a link: Check out our URL Shortener, SMS/Email, and Database Generator tools.", "", "Seeded", now),
        ]
        cur.executemany(
            "INSERT INTO social_posts (platform, handle, content, image_url, external_status, posted_at) VALUES (?, ?, ?, ?, ?, ?)",
            seed_posts,
        )

    conn.commit()
    conn.close()


init_social_db()


def publish_to_facebook(content: str) -> str:
    page_id = os.getenv("FB_PAGE_ID", "").strip()
    page_token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not page_token:
        return "Local DB (add FB_PAGE_ID & FB_PAGE_ACCESS_TOKEN for live FB Page)"

    res = requests.post(
        f"https://graph.facebook.com/v27.0/{page_id}/feed",
        headers={"Authorization": f"Bearer {page_token}"},
        data={"message": content},
        timeout=10,
    )
    res.raise_for_status()
    return f"Live FB Post ID: {res.json().get('id', 'ok')}"


def publish_to_instagram(content: str, image_url: str) -> str:
    ig_user_id = os.getenv("IG_USER_ID", "").strip()
    ig_token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    if not ig_user_id or not ig_token:
        return "Local DB (add IG_USER_ID & IG_ACCESS_TOKEN for live IG)"
    if not image_url:
        return "Local DB (IG API requires a public JPEG image_url)"

    create_res = requests.post(
        f"https://graph.facebook.com/v27.0/{ig_user_id}/media",
        data={"image_url": image_url, "caption": content, "access_token": ig_token},
        timeout=10,
    )
    create_res.raise_for_status()
    creation_id = create_res.json().get("id")

    pub_res = requests.post(
        f"https://graph.facebook.com/v27.0/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": ig_token},
        timeout=10,
    )
    pub_res.raise_for_status()
    return f"Live IG Media ID: {pub_res.json().get('id', 'ok')}"


def publish_to_x(content: str) -> str:
    bearer_or_user_token = os.getenv("X_USER_ACCESS_TOKEN", "").strip()
    if not bearer_or_user_token:
        return "Local DB (add X_USER_ACCESS_TOKEN for live X post)"

    res = requests.post(
        "https://api.x.com/2/tweets",
        headers={
            "Authorization": f"Bearer {bearer_or_user_token}",
            "Content-Type": "application/json",
        },
        json={"text": content[:280]},
        timeout=10,
    )
    res.raise_for_status()
    tweet_id = (res.json().get("data") or {}).get("id", "ok")
    return f"Live X Post ID: {tweet_id}"


@social_bp.route("/api/social/feed", methods=["GET"])
def get_social_feed():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    feed = {"IG": [], "X": [], "FB": []}
    for platform in ("IG", "X", "FB"):
        cur.execute(
            "SELECT * FROM social_posts WHERE platform = ? ORDER BY id DESC LIMIT 5",
            (platform,),
        )
        feed[platform] = [dict(row) for row in cur.fetchall()]

    conn.close()
    return jsonify({"feed": feed})


@social_bp.route("/api/social/post", methods=["POST"])
def create_social_post():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    image_url = (data.get("image_url") or "").strip()

    if not content:
        return jsonify({"error": "Post content is required"}), 400

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = {}

    for platform, handle, publisher in [
        ("IG", "@fuuroo", lambda: publish_to_instagram(content, image_url)),
        ("X", "@FuuRooWeb", lambda: publish_to_x(content)),
        ("FB", "/FuuRoo", lambda: publish_to_facebook(content)),
    ]:
        try:
            status_msg = publisher()
        except Exception as exc:
            status_msg = f"API Error ({exc}) — saved locally"
        results[platform] = status_msg

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO social_posts (platform, handle, content, image_url, external_status, posted_at) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("IG", "@fuuroo", content, image_url, results["IG"], timestamp),
            ("X", "@FuuRooWeb", content, image_url, results["X"], timestamp),
            ("FB", "/FuuRoo", content, image_url, results["FB"], timestamp),
        ],
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "posted_at": timestamp, "results": results})