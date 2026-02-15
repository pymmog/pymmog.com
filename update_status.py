#!/usr/bin/env python3
"""
Status page updater -- polls Spotify + Steam, fills in template.html,
and writes the result to the nginx web root.

Run via cron every 1-2 minutes.

Edit template.html directly to change styles, layout, or social links.
This script only handles data fetching and placeholder replacement.
"""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "template.html")
TOKEN_CACHE = os.path.join(SCRIPT_DIR, ".spotify_token_cache")


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_template():
    with open(TEMPLATE_PATH) as f:
        return f.read()


def html_esc(text):
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt_ms(ms):
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


def progress_bar(progress_ms, duration_ms, width=30):
    if duration_ms <= 0:
        return "─" * width
    ratio = min(progress_ms / duration_ms, 1.0)
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


# ── Spotify ────────────────────────────────────────────────────


def spotify_refresh_access_token(cfg):
    if os.path.exists(TOKEN_CACHE):
        with open(TOKEN_CACHE) as f:
            cache = json.load(f)
        if cache.get("timestamp", 0) > datetime.now(timezone.utc).timestamp() - 3000:
            return cache["access_token"]

    auth_header = base64.b64encode(
        f"{cfg['spotify_client_id']}:{cfg['spotify_client_secret']}".encode()
    ).decode()

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": cfg["spotify_refresh_token"],
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

    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"[spotify] token refresh failed: {e}", file=sys.stderr)
        return None

    with open(TOKEN_CACHE, "w") as f:
        json.dump(
            {
                "access_token": tokens["access_token"],
                "timestamp": datetime.now(timezone.utc).timestamp(),
            },
            f,
        )

    return tokens["access_token"]


def get_spotify_status(cfg):
    token = spotify_refresh_access_token(cfg)
    if not token:
        return None

    req = urllib.request.Request(
        "https://api.spotify.com/v1/me/player/currently-playing",
        headers={"Authorization": f"Bearer {token}"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                data = None
            else:
                data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"[spotify] API error: {e}", file=sys.stderr)
        data = None

    # If we got a current track, return it
    if data and data.get("item"):
        item = data["item"]
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        album = item.get("album", {}).get("name", "")
        album_art = ""
        images = item.get("album", {}).get("images", [])
        if images:
            album_art = sorted(images, key=lambda i: i.get("width", 999))[0]["url"]

        return {
            "track": item.get("name", "Unknown"),
            "artists": artists,
            "album": album,
            "album_art": album_art,
            "progress_ms": data.get("progress_ms", 0),
            "duration_ms": item.get("duration_ms", 1),
            "is_playing": data.get("is_playing", False),
            "last_played": False,
        }

    # Nothing currently playing -- try recently played
    req = urllib.request.Request(
        "https://api.spotify.com/v1/me/player/recently-played?limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            recent = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"[spotify] recently-played error: {e}", file=sys.stderr)
        return None

    items = recent.get("items", [])
    if not items:
        return None

    item = items[0].get("track", {})
    artists = ", ".join(a["name"] for a in item.get("artists", []))
    album = item.get("album", {}).get("name", "")
    album_art = ""
    images = item.get("album", {}).get("images", [])
    if images:
        album_art = sorted(images, key=lambda i: i.get("width", 999))[0]["url"]

    return {
        "track": item.get("name", "Unknown"),
        "artists": artists,
        "album": album,
        "album_art": album_art,
        "progress_ms": 0,
        "duration_ms": item.get("duration_ms", 1),
        "is_playing": False,
        "last_played": True,
    }


# ── Steam ──────────────────────────────────────────────────────


def get_steam_status(cfg):
    params = urllib.parse.urlencode(
        {
            "key": cfg["steam_api_key"],
            "steamids": cfg["steam_id"],
            "format": "json",
        }
    )
    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?{params}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"[steam] API error: {e}", file=sys.stderr)
        return None

    players = data.get("response", {}).get("players", [])
    if not players:
        return None

    player = players[0]
    state_map = {0: "Offline", 1: "Online", 2: "Busy", 3: "Away", 4: "Snooze", 5: "Online", 6: "Online"}
    state = state_map.get(player.get("personastate", 0), "Offline")
    game = player.get("gameextrainfo")

    # If not currently in a game, get the most recently played game
    # using GetOwnedGames which has rtime_last_played timestamps
    last_played_game = None
    if not game:
        owned_params = urllib.parse.urlencode(
            {
                "key": cfg["steam_api_key"],
                "steamid": cfg["steam_id"],
                "include_appinfo": 1,
                "include_played_free_games": 1,
                "format": "json",
            }
        )
        owned_url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?{owned_params}"

        try:
            req = urllib.request.Request(owned_url)
            with urllib.request.urlopen(req) as resp:
                owned_data = json.loads(resp.read().decode())
            games = owned_data.get("response", {}).get("games", [])
            if games:
                # Sort by rtime_last_played descending to get the most recent
                games.sort(key=lambda g: g.get("rtime_last_played", 0), reverse=True)
                last_played_game = games[0].get("name")
        except urllib.error.URLError as e:
            print(f"[steam] owned-games error: {e}", file=sys.stderr)

    return {
        "state": state,
        "game": game,
        "last_played_game": last_played_game,
    }


# ── Build placeholders ────────────────────────────────────────


def build_placeholders(spotify, steam):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    p = {}

    # Spotify
    if spotify and spotify["is_playing"]:
        p["SPOTIFY_STATUS"] = '<span class="blink">▶</span> NOW PLAYING'
        p["SPOTIFY_BODY"] = (
            f"    Track: {html_esc(spotify['track'])}\n"
            f"    Artist: {html_esc(spotify['artists'])}\n"
            f"    Album: {html_esc(spotify['album'])}\n"
            f"    Time: {fmt_ms(spotify['progress_ms'])} / {fmt_ms(spotify['duration_ms'])}\n"
            f"    [{progress_bar(spotify['progress_ms'], spotify['duration_ms'])}]"
        )
    elif spotify and not spotify["is_playing"] and not spotify.get("last_played"):
        p["SPOTIFY_STATUS"] = '<span class="muted">⏸</span> PAUSED'
        p["SPOTIFY_BODY"] = (
            f"    Track: {html_esc(spotify['track'])}\n"
            f"    Artist: {html_esc(spotify['artists'])}\n"
            f"    Album: {html_esc(spotify['album'])}"
        )
    elif spotify and spotify.get("last_played"):
        p["SPOTIFY_STATUS"] = '<span class="muted">■</span> LAST PLAYED'
        p["SPOTIFY_BODY"] = (
            f"    Track: {html_esc(spotify['track'])}\n"
            f"    Artist: {html_esc(spotify['artists'])}\n"
            f"    Album: {html_esc(spotify['album'])}"
        )
    else:
        p["SPOTIFY_STATUS"] = '<span class="muted">■</span> IDLE'
        p["SPOTIFY_BODY"] = '    <span class="muted">Nothing playing.</span>'

    # Steam
    if steam:
        if steam["game"]:
            p["STEAM_STATUS"] = '<span class="steam-playing blink">▶</span> IN-GAME'
            p["STEAM_BODY"] = (
                f'    Playing: <span class="hl">{html_esc(steam["game"])}</span>'
            )
        elif steam.get("last_played_game"):
            p["STEAM_STATUS"] = '<span class="muted">■</span> LAST PLAYED'
            p["STEAM_BODY"] = (
                f"    Game: {html_esc(steam['last_played_game'])}"
            )
        else:
            cls = "online" if steam["state"] == "Online" else "muted"
            p["STEAM_STATUS"] = f'<span class="{cls}">●</span> {html_esc(steam["state"]).upper()}'
            p["STEAM_BODY"] = '    <span class="muted">Nothing recent.</span>'
    else:
        p["STEAM_STATUS"] = '<span class="muted">●</span> UNKNOWN'
        p["STEAM_BODY"] = '    <span class="muted">Could not fetch Steam data.</span>'

    # Album art background
    if spotify and spotify.get("album_art"):
        p["ALBUM_ART_CSS"] = (
            f"\n    .album-ghost {{\n"
            f"        background-image: url('{spotify['album_art']}');\n"
            f"        background-size: cover;\n"
            f"        background-position: center;\n"
            f"        opacity: 0.035;\n"
            f"        position: fixed;\n"
            f"        top: 0; left: 0; right: 0; bottom: 0;\n"
            f"        pointer-events: none;\n"
            f"        z-index: 0;\n"
            f"        filter: blur(50px);\n"
            f"    }}"
        )
    else:
        p["ALBUM_ART_CSS"] = ""

    p["UPDATED"] = now
    return p


def render(template, placeholders):
    html = template
    for key, value in placeholders.items():
        html = html.replace("{{" + key + "}}", value)
    return html


# ── Main ──────────────────────────────────────────────────────


def main():
    cfg = load_config()
    template = load_template()

    spotify = get_spotify_status(cfg)
    steam = get_steam_status(cfg)

    placeholders = build_placeholders(spotify, steam)
    html = render(template, placeholders)

    output_path = cfg.get("output_path", "/var/www/html/index.html")

    # Write atomically
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(html)
    os.replace(tmp_path, output_path)

    print(f"[ok] updated {output_path} at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
