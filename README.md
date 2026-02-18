# pymmog.com

A lightweight personal status page that displays what you're listening to on Spotify and playing on Steam. Styled as a CRT terminal with the [Rosé Pine](https://rosepinetheme.com) theme and [Geist Pixel Circle](https://vercel.com/font) font.

Runs on a Raspberry Pi Zero 2W with nginx, exposed via Cloudflare Tunnel. The page is generated on-demand — when a visitor opens the site, a Python HTTP server fetches live data from Spotify and Steam and serves the result. No frameworks, no dependencies beyond Python 3 stdlib.

## Features

- Live Spotify track, falls back to last played
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
├── server.py            # Lightweight HTTP server — triggers update on each request
├── spotify_auth.py      # One-time OAuth setup for Spotify
├── config.json.example  # Template for API keys
└── .gitignore
```

## Requirements

- Python 3
- nginx
- systemd
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
2. Find your 64-bit Steam ID at [steamid.io](https://steamid.io)

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
    "spotify_client_id": "...",
    "spotify_client_secret": "...",
    "spotify_refresh_token": "...",
    "steam_api_key": "...",
    "steam_id": "...",
    "output_path": "/var/www/html/index.html"
}
```

### 6. Permissions

Make sure your user can write to the nginx web root:

```bash
sudo chown -R $(whoami):$(whoami) /var/www/html
```

### 7. systemd service

Create `/etc/systemd/system/pymmog.service`:

```ini
[Unit]
Description=pymmog status page server
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/pymmog.com/server.py
WorkingDirectory=/home/pi/pymmog.com
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl enable pymmog
sudo systemctl start pymmog
```

### 8. nginx

Open `/etc/nginx/sites-available/default` and replace the `location /` block with:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
}
```

Then test and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 9. Test

Visit your site — the page should generate live on the first request.

## How it works

1. A visitor opens the site
2. nginx proxies the request to `server.py` running on port 8080
3. `server.py` calls `update_status.py`, which fetches live data from Spotify and Steam
4. The script reads `template.html`, replaces the `{{PLACEHOLDER}}` tags with live data, and writes the result atomically to the nginx web root
5. `server.py` serves the freshly written file
6. The page auto-refreshes in the browser every 60 seconds

Spotify tokens are cached and refreshed automatically.

## Customizing

Edit `template.html` to change anything visual — colors, fonts, layout, CRT effects, social links. The Python script never needs to be touched for style changes.

The template uses these placeholders filled in by the script:

| Placeholder          | Content                                   |
|----------------------|-------------------------------------------|
| `{{SPOTIFY_STATUS}}` | NOW PLAYING / PAUSED / LAST PLAYED / IDLE |
| `{{SPOTIFY_BODY}}`   | Track, artist, album                      |
| `{{STEAM_STATUS}}`   | IN-GAME / LAST PLAYED / ONLINE / OFFLINE  |
| `{{STEAM_BODY}}`     | Current or last played game               |
| `{{ALBUM_ART_CSS}}`  | Blurred album art background              |
| `{{UPDATED}}`        | Timestamp                                 |

To swap to Rosé Pine Moon or Dawn, change the CSS variables in `:root`. Full palette at [rosepinetheme.com/palette](https://rosepinetheme.com/palette).

—

**Disclaimer:** This README.md was partially generated with AI assistance.
