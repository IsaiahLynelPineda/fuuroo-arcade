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

FEATURED_GAMES = {
    "ben10": {
        "id": "ben-10-savage-pursuit",
        "title": "Ben 10: Savage Pursuit",
        "tag": "2006",
        "archive_id": "Ben_10_Savage_Pursuit",
        "search_q": 'title:("Ben 10" AND "Savage Pursuit")',
        "cache_file": "ben10.swf",
        "desc": "Classic Cartoon Network Flash action platformer.",
    },
    "gunblood": {
        "id": "gunblood_flash",
        "title": "GunBlood",
        "tag": "2008",
        "archive_id": "gunblood_flash",
        "search_q": 'identifier:(gunblood_flash) OR title:("GunBlood")',
        "cache_file": "gunblood.swf",
        "desc": "Fast-paced Western duel Flash shootout game.",
    },
    "whackyourboss": {
        "id": "whack_your_boss_17ways",
        "title": "Whack Your Boss (17 Ways)",
        "tag": "2007",
        "archive_id": "whack_your_boss_17ways",
        "search_q": 'identifier:(whack_your_boss_17ways) OR title:("Whack Your Boss")',
        "cache_file": "whack_your_boss.swf",
        "desc": "Classic office stress-relief Flash point-and-click game.",
    },
}

FEATURED_TRACKS = [
    {
        "trackId": "opivy-take-warning",
        "trackName": "Take Warning",
        "artistName": "Operation Ivy",
        "genre": "Ska-Punk (1989)",
        "duration": "2:44",
        "archive_id": "1989-operation-ivy-energy",
        "keyword": "take warning",
        "cache_file": "opivy_take_warning.mp3",
        "artwork": "https://archive.org/services/img/1989-operation-ivy-energy",
        "previewUrl": "/api/media/audio_proxy?track=opivy-take-warning",
    },
    {
        "trackId": "opivy-sound-system",
        "trackName": "Sound System",
        "artistName": "Operation Ivy",
        "genre": "Ska-Punk (1989)",
        "duration": "2:14",
        "archive_id": "1989-operation-ivy-energy",
        "keyword": "sound system",
        "cache_file": "opivy_sound_system.mp3",
        "artwork": "https://archive.org/services/img/1989-operation-ivy-energy",
        "previewUrl": "/api/media/audio_proxy?track=opivy-sound-system",
    },
    {
        "trackId": "opivy-knowledge",
        "trackName": "Knowledge",
        "artistName": "Operation Ivy",
        "genre": "Ska-Punk (1989)",
        "duration": "1:42",
        "archive_id": "1989-operation-ivy-energy",
        "keyword": "knowledge",
        "cache_file": "opivy_knowledge.mp3",
        "artwork": "https://archive.org/services/img/1989-operation-ivy-energy",
        "previewUrl": "/api/media/audio_proxy?track=opivy-knowledge",
    },
]


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
        "q": "identifier:(TheGeneral1926 OR PhantasmagoriaTheater-Nosferatu1922909 OR Cops1922)",
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
                "desc": (d.get("description") or "Classic silent public domain film.")[:85] + "...",
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
    query = request.args.get("q", "").strip().lower()

    results = [
        {
            "id": g["id"],
            "title": g["title"],
            "tag": g["tag"],
            "thumb": f"https://archive.org/services/img/{g['archive_id']}",
            "embed": f"/api/media/swf_proxy?game={key}",
            "type": "swf",
            "desc": g["desc"],
        }
        for key, g in FEATURED_GAMES.items()
        if not query or query in g["title"].lower() or query in g["desc"].lower() or query in key
    ]
    return jsonify({"games": results})


@app.route("/api/media/swf_proxy")
def swf_proxy():
    game_key = request.args.get("game", "ben10").strip().lower()
    game_cfg = FEATURED_GAMES.get(game_key, FEATURED_GAMES["ben10"])

    local_swf = os.path.join(app.root_path, "static", "games", game_cfg["cache_file"])
    if os.path.exists(local_swf):
        return send_file(local_swf, mimetype="application/x-shockwave-flash")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
    }

    candidate_ids = [game_cfg["archive_id"]]
    try:
        search_res = requests.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": game_cfg["search_q"],
                "fl[]": ["identifier"],
                "output": "json",
                "rows": 8,
            },
            headers=headers,
            timeout=10,
        ).json()
        for doc in search_res.get("response", {}).get("docs", []):
            if doc["identifier"] not in candidate_ids:
                candidate_ids.append(doc["identifier"])
    except Exception:
        pass

    for ident in candidate_ids:
        try:
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
            continue

    return jsonify({"error": f"No valid SWF found for {game_cfg['title']}"}), 502


@app.route("/api/media/music")
def get_music():
    query = request.args.get("q", "").strip()
    headers = {"Accept": "application/json", "User-Agent": "FuuRooPortal/1.0"}

    # Default / Featured: return Operation Ivy tracks immediately
    if not query or query.lower() in ("featured", "operation ivy", "take warning", "ska", "punk"):
        return jsonify({"results": FEATURED_TRACKS})

    # Otherwise search Internet Archive Audio for full-length MP3 tracks
    try:
        search_res = requests.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": f"mediatype:(audio) AND ({query})",
                "fl[]": ["identifier", "title", "creator", "year"],
                "sort[]": "downloads desc",
                "output": "json",
                "rows": 6,
            },
            headers=headers,
            timeout=8,
        ).json()
        docs = search_res.get("response", {}).get("docs", [])

        tracks = []
        for doc in docs:
            ident = doc["identifier"]
            meta = requests.get(f"https://archive.org/metadata/{ident}", headers=headers, timeout=6).json()
            mp3_file = next(
                (f for f in meta.get("files", []) if f.get("name", "").lower().endswith(".mp3")),
                None,
            )
            if not mp3_file:
                continue

            fname = mp3_file["name"]
            length_raw = mp3_file.get("length", "Full")
            tracks.append({
                "trackId": ident,
                "trackName": doc.get("title") or fname.replace(".mp3", ""),
                "artistName": doc.get("creator") or "Internet Archive Audio",
                "genre": str(doc.get("year") or "Full MP3"),
                "duration": str(length_raw).split(".")[0],
                "artwork": f"https://archive.org/services/img/{ident}",
                "previewUrl": f"/api/media/audio_proxy?ident={ident}&file={requests.utils.quote(fname)}",
            })
            if len(tracks) >= 6:
                break

        return jsonify({"results": tracks or FEATURED_TRACKS})
    except Exception:
        return jsonify({"results": FEATURED_TRACKS})


@app.route("/api/media/audio_proxy")
def audio_proxy():
    track_id = request.args.get("track", "").strip()
    ident = request.args.get("ident", "").strip()
    fname = request.args.get("file", "").strip()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
    }

    # Case A: Featured track (e.g., Operation Ivy) -> look up exact MP3 filename & cache locally
    featured = next((t for t in FEATURED_TRACKS if t["trackId"] == track_id), None)
    if featured:
        local_mp3 = os.path.join(app.root_path, "static", "music", featured["cache_file"])
        if os.path.exists(local_mp3):
            return send_file(local_mp3, mimetype="audio/mpeg", conditional=True)

        try:
            meta = requests.get(
                f"https://archive.org/metadata/{featured['archive_id']}",
                headers=headers,
                timeout=10,
            ).json()
            mp3_files = [
                f.get("name", "")
                for f in meta.get("files", [])
                if f.get("name", "").lower().endswith(".mp3")
            ]
            matched = next(
                (name for name in mp3_files if featured["keyword"] in name.lower()),
                mp3_files[0] if mp3_files else None,
            )
            if matched:
                mp3_url = f"https://archive.org/download/{featured['archive_id']}/{requests.utils.quote(matched)}"
                r = requests.get(mp3_url, headers=headers, allow_redirects=True, timeout=20)
                if r.status_code == 200 and len(r.content) > 10000:
                    os.makedirs(os.path.dirname(local_mp3), exist_ok=True)
                    with open(local_mp3, "wb") as f:
                        f.write(r.content)
                    return send_file(local_mp3, mimetype="audio/mpeg", conditional=True)
        except Exception as e:
            return jsonify({"error": str(e)}), 502

    # Case B: Dynamic search result from Internet Archive
    if ident and fname:
        try:
            mp3_url = f"https://archive.org/download/{ident}/{requests.utils.quote(fname)}"
            r = requests.get(mp3_url, headers=headers, allow_redirects=True, timeout=20)
            if r.status_code == 200:
                return Response(r.content, content_type="audio/mpeg")
        except Exception as e:
            return jsonify({"error": str(e)}), 502

    return jsonify({"error": "Audio track not found"}), 404


if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)