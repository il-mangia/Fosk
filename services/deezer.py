"""
Deezer API integration for metadata enrichment.
Uses an in-memory cache (cleared on server restart as per requirements).
"""
import time
import httpx
from config import DEEZER_API_BASE, DEEZER_CACHE_TTL

# In-memory cache: key -> (timestamp, data)
_cache: dict[str, tuple[float, dict]] = {}


def _cache_get(key: str) -> dict | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < DEEZER_CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, data: dict) -> None:
    _cache[key] = (time.time(), data)


async def search_track(title: str, artist: str | None = None) -> dict | None:
    """
    Search Deezer for a track.  Returns enriched metadata dict or None.
    """
    query = f"{artist} {title}" if artist else title
    cache_key = f"search:{query.lower()}"

    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{DEEZER_API_BASE}/search",
                params={"q": query, "limit": 1},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[Deezer] Search failed for '{query}': {e}")
        return None

    tracks = data.get("data", [])
    if not tracks:
        return None

    t = tracks[0]
    result = {
        "title":     t.get("title_short") or t.get("title"),
        "artist":    t["artist"]["name"] if "artist" in t else None,
        "album":     t["album"]["title"] if "album" in t else None,
        "cover_url": t["album"].get("cover_xl") or t["album"].get("cover_big") if "album" in t else None,
        "duration":  t.get("duration"),
        "deezer_id": t.get("id"),
    }

    # Optionally fetch album details for year/genre
    album_id = t.get("album", {}).get("id")
    if album_id:
        album_data = await _fetch_album(client_or_none=None, album_id=album_id)
        if album_data:
            result["year"]  = album_data.get("year")
            result["genre"] = album_data.get("genre")

    _cache_set(cache_key, result)
    return result


async def _fetch_album(client_or_none, album_id: int) -> dict | None:
    cache_key = f"album:{album_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{DEEZER_API_BASE}/album/{album_id}")
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[Deezer] Album fetch failed for id={album_id}: {e}")
        return None

    genres = data.get("genres", {}).get("data", [])
    result = {
        "year":  data.get("release_date", "")[:4] or None,
        "genre": genres[0]["name"] if genres else None,
    }
    if result["year"]:
        result["year"] = int(result["year"])

    _cache_set(cache_key, result)
    return result


async def enrich_track(track: dict) -> dict:
    """
    Accepts a track dict and returns an enriched copy.
    Only fills fields that are empty/None in the original.
    """
    title  = track.get("title")
    artist = track.get("artist")

    if not title:
        return track   # nothing to search for

    deezer = await search_track(title, artist)
    if not deezer:
        return track

    enriched = dict(track)
    for field in ("title", "artist", "album", "cover_url", "duration", "year", "genre"):
        if not enriched.get(field) and deezer.get(field):
            enriched[field] = deezer[field]

    return enriched
