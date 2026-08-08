"""
Bmb YT-DLP API
A lightweight FastAPI service that resolves YouTube videos (by direct link
OR by song/video name) into direct, downloadable media URLs using yt-dlp —
which is actively maintained and adapts quickly to YouTube's changes.
"""

import re
from typing import Optional

import yt_dlp
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bmb YT-DLP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def resolve_input(value: str) -> str:
    """If the input is already a URL, use it as-is. Otherwise treat it as a
    search query (song/video name) and let yt-dlp resolve the top result."""
    value = value.strip()
    if URL_PATTERN.match(value):
        return value
    return f"ytsearch1:{value}"


def extract_info(query_or_url: str) -> dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extract_flat": False,
        "extractor_args": {
            "youtube": {"player_client": ["android", "web"]},
        },
        "http_headers": {
            "User-Agent": "com.google.android.youtube/19.29.37 (Linux; U; Android 14) gzip"
        },
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(resolve_input(query_or_url), download=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"yt-dlp error: {e}")

    if info is None:
        raise HTTPException(status_code=404, detail="Video not found")

    # ytsearch wraps the result in an "entries" list
    if "entries" in info:
        entries = [e for e in info["entries"] if e]
        if not entries:
            raise HTTPException(status_code=404, detail="No results found")
        info = entries[0]

    return info


def pick_progressive_video_formats(info: dict) -> list:
    """Formats that already have both video + audio combined (no ffmpeg
    merge needed) — safe to hand directly to a client as a downloadable file."""
    formats = info.get("formats") or []
    progressive = [
        f
        for f in formats
        if f.get("vcodec") not in (None, "none")
        and f.get("acodec") not in (None, "none")
        and f.get("url")
    ]
    progressive.sort(key=lambda f: f.get("height") or 0, reverse=True)

    results = []
    seen_heights = set()
    for f in progressive:
        height = f.get("height")
        if height in seen_heights:
            continue
        seen_heights.add(height)
        results.append(
            {
                "quality": f"{height}p" if height else f.get("format_note", "unknown"),
                "ext": f.get("ext"),
                "filesizeMB": round(f["filesize"] / 1024 / 1024, 2)
                if f.get("filesize")
                else None,
                "url": f["url"],
            }
        )
    return results


def pick_best_audio_format(info: dict) -> Optional[dict]:
    formats = info.get("formats") or []
    audio_only = [
        f
        for f in formats
        if f.get("vcodec") in (None, "none")
        and f.get("acodec") not in (None, "none")
        and f.get("url")
    ]
    if not audio_only:
        return None
    audio_only.sort(key=lambda f: f.get("abr") or 0, reverse=True)
    best = audio_only[0]
    return {
        "quality": f"{int(best['abr'])}kbps" if best.get("abr") else "unknown",
        "ext": best.get("ext"),
        "filesizeMB": round(best["filesize"] / 1024 / 1024, 2)
        if best.get("filesize")
        else None,
        "url": best["url"],
    }


@app.get("/", tags=["meta"])
async def root():
    return {"name": "Bmb YT-DLP API", "version": "1.0.0", "status": "ok"}


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}


@app.get("/search", tags=["search"])
async def search(q: str = Query(..., description="Song or video name to search for")):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extractor_args": {
            "youtube": {"player_client": ["android", "web"]},
        },
        "http_headers": {
            "User-Agent": "com.google.android.youtube/19.29.37 (Linux; U; Android 14) gzip"
        },
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{q}", download=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"yt-dlp error: {e}")

    entries = info.get("entries") or []
    results = [
        {
            "videoId": e.get("id"),
            "title": e.get("title"),
            "channel": e.get("uploader"),
            "duration": e.get("duration"),
            "thumbnail": e.get("thumbnail"),
            "url": f"https://www.youtube.com/watch?v={e.get('id')}",
        }
        for e in entries
        if e
    ]
    return {"success": True, "query": q, "results": results}


@app.get("/video", tags=["download"])
async def get_video(
    url: Optional[str] = Query(None, description="Direct YouTube URL"),
    q: Optional[str] = Query(None, description="Song/video name to search for"),
):
    target = url or q
    if not target:
        raise HTTPException(status_code=400, detail="Provide 'url' or 'q'.")

    info = extract_info(target)
    formats = pick_progressive_video_formats(info)
    if not formats:
        raise HTTPException(
            status_code=404, detail="No downloadable video formats found."
        )

    return {
        "success": True,
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "channel": info.get("uploader"),
        "formats": formats,
    }


@app.get("/audio", tags=["download"])
async def get_audio(
    url: Optional[str] = Query(None, description="Direct YouTube URL"),
    q: Optional[str] = Query(None, description="Song/video name to search for"),
):
    target = url or q
    if not target:
        raise HTTPException(status_code=400, detail="Provide 'url' or 'q'.")

    info = extract_info(target)
    audio = pick_best_audio_format(info)
    if not audio:
        raise HTTPException(
            status_code=404, detail="No downloadable audio format found."
        )

    return {
        "success": True,
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "channel": info.get("uploader"),
        "audio": audio,
    }
