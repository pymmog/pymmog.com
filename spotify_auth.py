#!/usr/bin/env python3
"""
Spotify OAuth2 Authorization - Run once to get your refresh token.

Usage:
  1. Create an app at https://developer.spotify.com/dashboard
  2. Set redirect URI to: http://localhost:8888/callback
  3. Fill in CLIENT_ID and CLIENT_SECRET below
  4. Run: python3 spotify_auth.py
  5. Open the URL it prints in your browser
  6. After authorizing, paste the full redirect URL back into the terminal
  7. Save the refresh_token it outputs into your config.json
"""

import base64
import json
import urllib.parse
import urllib.request

# ── Fill these in ──────────────────────────────────────────────
CLIENT_ID = "YOUR_SPOTIFY_CLIENT_ID"
CLIENT_SECRET = "YOUR_SPOTIFY_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:8888/callback"
# ───────────────────────────────────────────────────────────────

SCOPES = "user-read-currently-playing user-read-playback-state user-read-recently-played"

AUTH_URL = (
    "https://accounts.spotify.com/authorize?"
    + urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
        }
    )
)

print("=" * 60)
print("Open this URL in your browser:")
print()
print(AUTH_URL)
print()
print("=" * 60)
print()

redirect_response = input("Paste the full redirect URL here: ").strip()

# Extract the code from the redirect URL
parsed = urllib.parse.urlparse(redirect_response)
code = urllib.parse.parse_qs(parsed.query)["code"][0]

# Exchange code for tokens
auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
data = urllib.parse.urlencode(
    {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
).encode()

req = urllib.request.Request(
    "https://accounts.spotify.com/api/token",
    data=data,
    headers={
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    },
)

with urllib.request.urlopen(req) as resp:
    tokens = json.loads(resp.read().decode())

print()
print("=" * 60)
print("SUCCESS! Save these values in your config.json:")
print()
print(f'  "spotify_client_id": "{CLIENT_ID}",')
print(f'  "spotify_client_secret": "{CLIENT_SECRET}",')
print(f'  "spotify_refresh_token": "{tokens["refresh_token"]}"')
print()
print("=" * 60)
