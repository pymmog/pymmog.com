# website

A lightweight personal status page that displays what you’re listening to on Spotify and playing on Steam. Styled as a CRT terminal with the [Rosé Pine](https://rosepinetheme.com) theme and [Geist Pixel Circle](https://vercel.com/font) font.

Runs on a Raspberry Pi Zero 2W with nginx, updated every minute via cron. No frameworks, no dependencies beyond Python 3 stdlib.

## Features

- Live Spotify track with progress bar, falls back to last played
- Current Steam game, falls back to last played
- CRT effects — scanlines, vignette, flicker, phosphor glow, RGB fringing
- Rosé Pine color scheme
- Auto-refreshes in the browser every 60s
- Styles live in a separate `template.html` — edit without touching Python

## Requirements

- Python 3
- nginx (or any web server that serves static files)
- Spotify Developer account
- Steam API key
- Public Steam profile (Game Details set to Public)

## Setup

### Spotify

1. Create an app at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Set redirect URI to `http://localhost:8888/callback`
3. Edit `spotify_auth.py` with your Client ID and Client Secret
4. Run `python3 spotify_auth.py`, open the URL, authorize, paste the redirect URL back
5. Save the printed refresh token

### Steam

1. Get an API key at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)
2. Find your 64-bit Steam ID at [steamid.io](https://steamid.io)

### Font

Download [Geist Pixel Circle](https://github.com/vercel/geist-font/releases) and place `GeistPixel-Circle.woff2` in your web root under `/fonts/`:

```bash
mkdir -p /var/www/html/fonts
cp GeistPixel-Circle.woff2 /var/www/html/fonts/
```

The template also tries loading from jsDelivr CDN as a fallback.

### Config

```bash
cp config.json.example config.json
```

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

### Run

```bash
python3 update_status.py
```

### Cron

```bash
crontab -e
```

```
* * * * * /usr/bin/python3 /home/pi/status-page/update_status.py >> /tmp/status-update.log 2>&1
```

## How it works

Cron runs `update_status.py` every minute. The script polls the Spotify and Steam APIs, fills in the placeholders in `template.html`, and writes the result to your nginx web root. The write is atomic (`.tmp` then `os.replace`) so nginx never serves a partial file.

Spotify tokens are cached and refreshed automatically.

## Customization

All styles, layout, and social links live in `template.html`. The Python script only does data fetching and fills in these placeholders:

| Placeholder | Content |
|—|—|
| `{{SPOTIFY_STATUS}}` | NOW PLAYING / PAUSED / LAST PLAYED / IDLE |
| `{{SPOTIFY_BODY}}` | Track, artist, album, progress bar |
| `{{STEAM_STATUS}}` | IN-GAME / LAST PLAYED / ONLINE / OFFLINE |
| `{{STEAM_BODY}}` | Current or last played game |
| `{{ALBUM_ART_CSS}}` | Blurred album art background |
| `{{UPDATED}}` | Timestamp |

To swap to Rosé Pine Moon or Dawn, change the CSS variables in `:root`. Full palette at [rosepinetheme.com/palette](https://rosepinetheme.com/palette).

—

**Disclaimer:** This README.md was partially generated with AI assistance.
