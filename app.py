import os
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, send_file
from google_auth_oauthlib.flow import Flow
from routes_utilities import utils_bp

# Allow OAuth 2.0 over http://localhost for local university demo
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = "fuuroo_super_secret_web2_portal_key"
app.register_blueprint(utils_bp)

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
    query = request.args.get("q", "").strip()
    collection = request.args.get("cat", "softwarelibrary_flash").strip()

    if not query:
        return jsonify({
            "games": [
                {
                    "id": "ben-10-savage-pursuit",
                    "title": "Ben 10: Savage Pursuit",
                    "tag": "2006",
                    "thumb": "https://archive.org/services/img/Ben_10_Savage_Pursuit",
                    "embed": "/api/media/swf_proxy",
                    "type": "swf",
                    "desc": "Classic Cartoon Network Flash action platformer.",
                }
            ]
        })

    url = "https://archive.org/advancedsearch.php"
    params = {
        "q": f"collection:({collection}) AND mediatype:(software) AND title:({query})",
        "fl[]": ["identifier", "title", "year", "creator"],
        "sort[]": "downloads desc",
        "output": "json",
        "rows": 3,
    }
    try:
        res = requests.get(url, params=params, timeout=8).json()
        docs = res.get("response", {}).get("docs", [])
        games = [
            {
                "id": d["identifier"],
                "title": d.get("title", d["identifier"]),
                "tag": str(d.get("year", "Flash SWF")),
                "thumb": f"https://archive.org/services/img/{d['identifier']}",
                "embed": f"https://archive.org/embed/{d['identifier']}",
                "type": "iframe",
                "desc": f"Classic Flash game ({d.get('creator', 'Cartoon Network / Y8')}).",
            }
            for d in docs
        ]
        if games:
            return jsonify({"games": games})
    except Exception:
        pass

    return jsonify({"games": []})


@app.route("/api/media/swf_proxy")
def swf_proxy():
    local_swf = os.path.join(app.root_path, "static", "games", "ben10.swf")
    if os.path.exists(local_swf):
        return send_file(local_swf, mimetype="application/x-shockwave-flash")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
    }

    # Dynamically search Internet Archive items and inspect their file lists for a real .swf
    try:
        search_res = requests.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": 'title:("Ben 10" AND "Savage Pursuit")',
                "fl[]": ["identifier"],
                "output": "json",
                "rows": 10,
            },
            headers=headers,
            timeout=10,
        ).json()

        for doc in search_res.get("response", {}).get("docs", []):
            ident = doc["identifier"]
            meta = requests.get(f"https://archive.org/metadata/{ident}", headers=headers, timeout=10).json()
            for file_info in meta.get("files", []):
                fname = file_info.get("name", "")
                if fname.lower().endswith(".swf"):
                    swf_url = f"https://archive.org/download/{ident}/{requests.utils.quote(fname)}"
                    r = requests.get(swf_url, headers=headers, allow_redirects=True, timeout=15)
                    if r.status_code == 200 and r.content[:3] in (b"FWS", b"CWS", b"ZWS"):
                        os.makedirs(os.path.dirname(local_swf), exist_ok=True)
                        with open(local_swf, "wb") as f:
                            f.write(r.content)
                        return Response(r.content, content_type="application/x-shockwave-flash")
    except Exception:
        pass

    return jsonify({"error": "No valid SWF binary found; place ben10.swf in static/games/"}), 502


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