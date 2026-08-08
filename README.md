# Bmb YT-DLP API

A lightweight FastAPI service that resolves YouTube videos — by direct link
**or by song/video name** — into direct, downloadable media URLs using
[yt-dlp](https://github.com/yt-dlp/yt-dlp), which is actively maintained and
adapts quickly to YouTube's changes (unlike many older scraping libraries).

## Endpoints

- `GET /search?q=<name>` — search YouTube by song/video name, returns top 10 results
- `GET /video?url=<youtube_url>` or `?q=<name>` — get direct downloadable video URLs (multiple qualities, video+audio already combined, no extra processing needed)
- `GET /audio?url=<youtube_url>` or `?q=<name>` — get the best direct downloadable audio-only URL
- `GET /health` — health check

All endpoints accept **either** a direct YouTube `url` **or** a search `q` (song/video name) — if you pass a name instead of a link, it automatically searches and uses the top result.

## Deploy on Render (recommended, free tier available)

1. Push this folder to a new GitHub repo (e.g. `Bmb-Ytdlp-Api`)
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect the repo
4. Render will detect the `Dockerfile` automatically — just click **Create Web Service**
5. Wait for it to deploy — you'll get a URL like `https://bmb-ytdlp-api.onrender.com`

## Deploy locally (test first)

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Then test:
```
http://localhost:8000/video?q=Alan Walker Spectre
http://localhost:8000/audio?url=https://youtu.be/xxxxxxxxxxx
```

## Notes

- `yt-dlp` requires periodic updates to keep working as YouTube changes — on Render, redeploying will pick up the latest `yt-dlp` version from `requirements.txt` (consider bumping the version occasionally, or removing the pin to always get latest).
- Video endpoint intentionally only returns **progressive** formats (video+audio already merged by YouTube) to avoid needing `ffmpeg` — this caps video quality around 720p, which is a reasonable tradeoff for a lightweight deploy.
