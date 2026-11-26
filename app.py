import os
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from google_auth_oauthlib.flow import Flow

# Allow OAuth 2.0 over http://localhost for local university demo
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = "fuuroo_super_secret_web2_portal_key"

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
REDIRECT_URI = "http://localhost:5000/callback"


# ================= MAIN PORTAL ROUTE =================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/session")
def get_session():
    return jsonify({
        "logged_in": "user" in session,
        "user": session.get("user"),
        "method": session.get("method"),
    })


# ================= MODULE 1 & 2: AUTH & GOOGLE OAUTH 2.0 =================
@app.route("/login/local", methods=["POST"])
def login_local():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if username and password:
        session["user"] = username
        session["method"] = "Local Account"
        return jsonify({"success": True, "user": username, "method": "Local Account"})
    return jsonify({"success": False, "error": "Username and password required"}), 400


@app.route("/login/google")
def login_google():
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return "Missing client_secret.json in FuuRoo folder!", 500

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account",
    )
    session["state"] = state
    session["code_verifier"] = flow.code_verifier
    return redirect(authorization_url)


@app.route("/callback")
def oauth_callback():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=session.get("state"),
        redirect_uri=REDIRECT_URI,
    )
    flow.code_verifier = session.get("code_verifier")
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    # Fetch Google profile info via Google OAuth2 UserInfo REST API
    userinfo_res = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"},
        timeout=10,
    ).json()

    email = userinfo_res.get("email", "google_user@gmail.com")
    session["user"] = email
    session["method"] = "Google OAuth 2.0"
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


# ================= MODULE 3A: MEDIA & ENTERTAINMENT APIs =================
@app.route("/api/media/videos")
def get_videos():
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": "identifier:(night_of_the_living_dead OR superman_mechanical_monsters OR Plan_9_from_Outer_Space_1959)",
        "fl[]": ["identifier", "title", "year", "description"],
        "output": "json",
        "rows": 3,
    }
    try:
        res = requests.get(url, params=params, timeout=8).json()
        docs = res.get("response", {}).get("docs", [])
        videos = [
            {
                "title": d.get("title", d["identifier"]),
                "tag": str(d.get("year", "Classic")),
                "embed": f"https://archive.org/embed/{d['identifier']}",
                "desc": (d.get("description") or "Classic public domain film.")[:85] + "...",
            }
            for d in docs
        ]
        if videos:
            return jsonify({"videos": videos})
    except Exception:
        pass

    return jsonify({"videos": []})


@app.route("/api/media/games")
def get_games():
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": "identifier:(arcade_mslug OR arcade_ffight OR arcade_shocktro)",
        "fl[]": ["identifier", "title", "year"],
        "output": "json",
        "rows": 3,
    }
    try:
        res = requests.get(url, params=params, timeout=8).json()
        docs = res.get("response", {}).get("docs", [])
        games = [
            {
                "title": d.get("title", d["identifier"]),
                "tag": str(d.get("year", "Arcade")),
                "embed": f"https://archive.org/embed/{d['identifier']}",
                "desc": "Playable Internet Archive MAME arcade cabinet.",
            }
            for d in docs
        ]
        if games:
            return jsonify({"games": games})
    except Exception:
        pass

    return jsonify({"games": []})


@app.route("/api/media/music")
def get_music():
    query = request.args.get("q", "2000s pop")
    res = requests.get(
        "https://itunes.apple.com/search",
        params={"term": query, "media": "music", "limit": 3},
        timeout=8,
    ).json()
    return jsonify({"results": res.get("results", [])})


if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)