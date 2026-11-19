import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
app.secret_key = "fuuroo_super_secret_arcade_key"

# Allow OAuth over http://localhost for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

LOCAL_USERS = {
    "player_one": "fuuroo1234",
    "admin": "admin123"
}

@app.route("/")
def index():
    return render_template(
        "index.html",
        user=session.get("user"),
        auth_method=session.get("auth_method")
    )

# 1. LOCAL LOGIN ROUTE
@app.route("/login/local", methods=["POST"])
def login_local():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if username in LOCAL_USERS and LOCAL_USERS[username] == password:
        session["user"] = username
        session["auth_method"] = "LOCAL SYSTEM"
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "INVALID CREDENTIALS"})

# 2. GOOGLE OAUTH 2.0 LOGIN ROUTE
@app.route("/login/google")
def login_google():
    if os.path.exists("client_secret.json"):
        flow = Flow.from_client_secrets_file(
            "client_secret.json",
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"
            ],
            redirect_uri=url_for("oauth_callback", _external=True)
        )
        authorization_url, state = flow.authorization_url(prompt="consent")
        session["state"] = state
        session["code_verifier"] = flow.code_verifier
        return redirect(authorization_url)
    else:
        session["user"] = "player_one@gmail.com"
        session["auth_method"] = "GOOGLE OAUTH 2.0 (DEMO MODE)"
        return redirect(url_for("index"))

@app.route("/callback")
def oauth_callback():
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        state=session["state"],
        redirect_uri=url_for("oauth_callback", _external=True)
    )
    flow.code_verifier = session.get("code_verifier")
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"}
    ).json()

    session["user"] = user_info.get("email", "google_player@gmail.com")
    session["auth_method"] = "GOOGLE OAUTH 2.0"
    return redirect(url_for("index"))

# 3. MODULE 3A: 3 RETRO ARCADE GAMES VIA LIVE INTERNET ARCHIVE API
@app.route("/api/games")
def get_games():
    badges = ["HOT", "RETRO", "NEW"]

    game_queries = [
        "title:(Metal Slug) AND collection:(internetarcade) AND mediatype:(software)",
        "title:(Final Fight) AND collection:(internetarcade) AND mediatype:(software)",
        "title:(Shock Troopers) AND collection:(internetarcade) AND mediatype:(software)"
    ]

    games = []
    api_connected = False

    for idx, query in enumerate(game_queries):
        try:
            res = requests.get(
                "https://archive.org/advancedsearch.php",
                params={
                    "q": query,
                    "fl[]": ["identifier", "title", "year", "creator", "downloads", "description"],
                    "sort[]": "downloads desc",
                    "rows": 1,
                    "output": "json"
                },
                timeout=5
            )
            res.raise_for_status()
            docs = res.json().get("response", {}).get("docs", [])

            if docs:
                doc = docs[0]
                identifier = doc.get("identifier", "")
                creator = doc.get("creator", "Classic Arcade")
                publisher = creator[0] if isinstance(creator, list) else str(creator)
                desc = doc.get("description", "Classic arcade cabinet streamed via Internet Archive API.")
                if isinstance(desc, list):
                    desc = desc[0]

                games.append({
                    "id": identifier,
                    "embed_url": f"https://archive.org/embed/{identifier}",
                    "title": str(doc.get("title", "ARCADE CABINET")).upper(),
                    "genre": "Retro Arcade",
                    "year": str(doc.get("year", "1990s")),
                    "publisher": publisher[:28],
                    "plays": f"{int(doc.get('downloads', 0)):,}",
                    "short_description": str(desc)[:95] + "...",
                    "badge": badges[idx % 3]
                })
                api_connected = True
        except Exception:
            continue

    source_label = (
        "LIVE INTERNET ARCHIVE ARCADE API (3 ACTIVE CABINETS)"
        if api_connected
        else "API CONNECTION ISSUE"
    )
    return jsonify({"source": source_label, "games": games})

# 4. LOGOUT ROUTE
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)