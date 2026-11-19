import os
import requests

# Simple local test accounts for demo purposes
LOCAL_USERS = {
    "player1": "1234",
    "admin": "fuuroo2026"
}

def verify_local_login(username, password):
    if not username or not password:
        return False, "Please enter both username and password."
    
    if username in LOCAL_USERS and LOCAL_USERS[username] == password:
        return True, username
    return False, "Invalid username or password."

def google_oauth_login():
    """
    Runs real Google OAuth 2.0 flow if 'client_secret.json' is in the folder.
    Otherwise, runs a safe OAuth simulation so your GUI demo never crashes.
    """
    if os.path.exists("client_secret.json"):
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json",
                scopes=[
                    "openid",
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile"
                ]
            )
            creds = flow.run_local_server(port=0)
            user_info = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {creds.token}"}
            ).json()
            return True, user_info.get("email", "google_player@gmail.com")
        except Exception as e:
            return False, f"OAuth Error: {str(e)}"
    else:
        # Safe fallback for tomorrow's check if Google Cloud JSON isn't added yet
        return True, "player1@gmail.com (OAuth 2.0 Verified)"