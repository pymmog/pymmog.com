# pymmog.com

A lightweight personal status page that displays what you’re listening to on Spotify and playing on Steam. Styled as a CRT terminal with the [Rosé Pine](https://rosepinetheme.com) theme and [Geist Pixel Circle](https://vercel.com/font) font.

Runs on a Raspberry Pi Zero 2W with nginx, exposed via Cloudflare Tunnel, updated every minute via cron. No frameworks, no dependencies beyond Python 3 stdlib.

## Features

- Live Spotify track with progress bar, falls back to last played
- Current Steam game, falls back to last played
- CRT effects — scanlines, vignette, flicker, phosphor glow, RGB fringing
- Rosé Pine color scheme
- Auto-refreshes in the browser every 60s
- Styles and layout live in `template.html` — edit without touching Python

## Project structure

```
pymmog.com/
├── template.html        # HTML, CSS, layout, social links — all visual stuff
├── update_status.py     # Fetches Spotify + Steam data, fills template, writes HTML
├── spotify_auth.py      # One-time OAuth setup for Spotify
├── config.json.example  # Template for API keys
└── .gitignore
```

## Requirements

- Python 3
- nginx (or any static file server)
- Spotify Developer account
- Steam API key
- Public Steam profile (Game Details set to Public)

## Setup

### 1. Clone

```bash
git clone https://github.com/pymmog/pymmog.com.git
cd pymmog.com
```

### 2. Spotify

1. Create an app at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Set redirect URI to `http://localhost:8888/callback`
3. Edit `spotify_auth.py` with your Client ID and Client Secret
4. Run `python3 spotify_auth.py`, open the URL, authorize, paste the redirect URL back
5. Save the printed refresh token

### 3. Steam

1. Get an API key at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)
1. Find your 64-bit Steam ID at [steamid.io](https://steamid.io)

### 4. Font

Download [Geist Pixel Circle](https://github.com/vercel/geist-font/releases) and place `GeistPixel-Circle.woff2` in your web root:

```bash
sudo mkdir -p /var/www/html/fonts
sudo cp GeistPixel-Circle.woff2 /var/www/html/fonts/
```

The template also tries loading from jsDelivr CDN as a fallback.

### 5. Config

```bash
cp config.json.example config.json
```

Fill in your API keys:

```json
{
    “spotify_client_id”: “...”,
    “spotify_client_secret”: “...”,
    “spotify_refresh_token”: “...”,
    “steam_api_key”: “...”,
    “steam_id”: “...”,
    “output_path”: “/var/www/html/index.html”
}
```

### 6. Permissions

Make sure your user can write to the nginx web root:

```bash
sudo chown -R $(whoami):$(whoami) /var/www/html
```

### 7. Test

```bash
python3 update_status.py
```

### 8. Cron

```bash
crontab -e
```

```
* * * * * /usr/bin/python3 /home/pi/pymmog.com/update_status.py >> /tmp/status-update.log 2>&1
```

## How it works

1. Cron runs `update_status.py` every minute
2. The script fetches data from Spotify and Steam APIs
3. It reads `template.html` and replaces the `{{PLACEHOLDER}}` tags with live data
4. The result is written atomically to the nginx web root
5. The page auto-refreshes in the browser every 60 seconds

Spotify tokens are cached and refreshed automatically.

## Customizing

Edit `template.html` to change anything visual — colors, fonts, layout, CRT effects, social links. The Python script never needs to be touched for style changes.

The template uses these placeholders that get filled in by the script:

|Placeholder         |Content                                  |
|-|-|
|`{{SPOTIFY_STATUS}}`|NOW PLAYING / PAUSED / LAST PLAYED / IDLE|
|`{{SPOTIFY_BODY}}`  |Track, artist, album, progress bar       |
|`{{STEAM_STATUS}}`  |IN-GAME / LAST PLAYED / ONLINE / OFFLINE |
|`{{STEAM_BODY}}`    |Current or last played game              |
|`{{ALBUM_ART_CSS}}` |Blurred album art background             |
|`{{UPDATED}}`       |Timestamp                                |

To swap to Rosé Pine Moon or Dawn, change the CSS variables in `:root`. Full palette at [rosepinetheme.com/palette](https://rosepinetheme.com/palette).

—

**Disclaimer:** This README.md was partially generated with AI assistance.
