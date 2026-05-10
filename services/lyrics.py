"""
Lyrics service using lrclib.net — a free, open-source lyrics API.
Returns both plain text and synced (LRC) lyrics when available.
No API key required.
"""
import httpx
from config import LRCLIB_API_BASE


async def get_lyrics(title: str, artist: str, duration: float = 0) -> dict:
    """
    Fetch lyrics for a track.
    Returns:
        {
            "synced": [ {"time": 12.34, "text": "Line..."}, ... ] | None,
            "plain":  "Full plain text..." | None,
            "source": "lrclib" | None,
        }
    """
    params = {"track_name": title, "artist_name": artist}
    if duration:
        params["duration"] = int(duration)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{LRCLIB_API_BASE}/get", params=params)
            if resp.status_code == 404:
                # Try search fallback
                return await _search_fallback(title, artist)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[Lyrics] Request failed for '{title}' by '{artist}': {e}")
        return {"synced": None, "plain": None, "source": None}

    synced_raw = data.get("syncedLyrics")
    plain_raw  = data.get("plainLyrics")

    return {
        "synced": _parse_lrc(synced_raw) if synced_raw else None,
        "plain":  plain_raw,
        "source": "lrclib",
    }


async def _search_fallback(title: str, artist: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{LRCLIB_API_BASE}/search",
                params={"track_name": title, "artist_name": artist},
            )
            resp.raise_for_status()
            results = resp.json()
    except Exception:
        return {"synced": None, "plain": None, "source": None}

    if not results:
        return {"synced": None, "plain": None, "source": None}

    best = results[0]
    synced_raw = best.get("syncedLyrics")
    plain_raw  = best.get("plainLyrics")
    return {
        "synced": _parse_lrc(synced_raw) if synced_raw else None,
        "plain":  plain_raw,
        "source": "lrclib",
    }


def _parse_lrc(lrc_text: str) -> list[dict]:
    """
    Parse LRC format into a list of {"time": float, "text": str} dicts.
    LRC line format: [mm:ss.xx] Lyric line
    """
    import re
    lines = []
    pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")

    for raw_line in lrc_text.splitlines():
        m = pattern.match(raw_line.strip())
        if m:
            minutes = int(m.group(1))
            seconds = float(m.group(2))
            text    = m.group(3).strip()
            time_s  = minutes * 60 + seconds
            lines.append({"time": time_s, "text": text})

    lines.sort(key=lambda x: x["time"])
    return lines
