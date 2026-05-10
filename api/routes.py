"""
All API routes for Fosk.
Mounted at /api by main.py.
"""
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import FileResponse

from database import db
from scanner.folder_scan import (
    scan_root, get_all_folders, get_folder, get_folder_tracks,
    get_subtree_tracks, get_children_folders, get_track_cover,
)
from services.deezer    import enrich_track
from services.lyrics    import get_lyrics
from services.discovery import get_discovery, get_similar, record_play
from player.stream      import stream_file

router = APIRouter()


# ─── Folders ─────────────────────────────────────────────────────────────────

@router.get("/folders")
async def list_folders():
    folders = await get_all_folders()
    return {"folders": folders}


@router.get("/folder/{folder_id}")
async def folder_detail(folder_id: int):
    folder = await get_folder(folder_id)
    if not folder:
        raise HTTPException(404, "Folder not found")
    tracks   = await get_folder_tracks(folder_id)
    children = await get_children_folders(folder_id)
    return {"folder": folder, "tracks": tracks, "children": children}


@router.get("/folder/{folder_id}/all")
async def folder_detail_all(folder_id: int):
    """Return tracks from this folder AND all nested subfolders."""
    folder = await get_folder(folder_id)
    if not folder:
        raise HTTPException(404, "Folder not found")
    tracks   = await get_subtree_tracks(folder_id)
    children = await get_children_folders(folder_id)
    return {"folder": folder, "tracks": tracks, "children": children}


@router.post("/scan")
async def scan(body: dict):
    """
    Trigger a library scan.
    Body: {"path": "/path/to/music"}
    """
    path = body.get("path")
    if not path:
        raise HTTPException(400, "Missing 'path' in body")
    try:
        result = await scan_root(path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except NotADirectoryError as e:
        raise HTTPException(400, str(e))
    return result


# ─── Tracks ──────────────────────────────────────────────────────────────────

@router.get("/track/{track_id}")
async def track_detail(track_id: int, enrich: bool = False):
    track = await db.fetchone("SELECT * FROM tracks WHERE id = ?", (track_id,))
    if not track:
        raise HTTPException(404, "Track not found")
    if enrich:
        track = await enrich_track(track)
    return track


@router.get("/track/{track_id}/enrich")
async def track_enrich(track_id: int):
    """Fetch Deezer metadata and return enriched track (does NOT persist)."""
    track = await db.fetchone("SELECT * FROM tracks WHERE id = ?", (track_id,))
    if not track:
        raise HTTPException(404, "Track not found")
    return await enrich_track(dict(track))


# ─── Streaming & Download ────────────────────────────────────────────────────

@router.get("/stream/{track_id}")
async def stream_track(track_id: int, request: Request):
    track = await db.fetchone("SELECT path FROM tracks WHERE id = ?", (track_id,))
    if not track:
        raise HTTPException(404, "Track not found")
    return await stream_file(Path(track["path"]), request)


@router.get("/download/{track_id}")
async def download_track(track_id: int):
    track = await db.fetchone("SELECT path, filename FROM tracks WHERE id = ?", (track_id,))
    if not track:
        raise HTTPException(404, "Track not found")
    path = Path(track["path"])
    if not path.exists():
        raise HTTPException(404, "File missing on disk")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=track["filename"],
    )


@router.get("/stats")
async def get_stats():
    """Return library statistics."""
    tracks = await db.fetchone("SELECT COUNT(*) as count, SUM(duration) as duration FROM tracks")
    folders = await db.fetchone("SELECT COUNT(*) as count FROM folders")
    return {
        "tracks": tracks["count"] or 0,
        "duration": tracks["duration"] or 0,
        "folders": folders["count"] or 0
    }


@router.get("/tracks/all")
async def get_all_tracks():
    """Return every track in the library for global playback."""
    rows = await db.fetchall(
        "SELECT id, title, artist, album, duration, year, genre, is_favorite FROM tracks"
    )
    return {"tracks": rows}


@router.post("/reset")
async def reset_db():
    """Clear all data from the database."""
    await db.execute("DELETE FROM tracks")
    await db.execute("DELETE FROM folders")
    await db.execute("DELETE FROM plays")
    await db.execute("DELETE FROM devices")
    await db.commit()
    _COVER_CACHE.clear()
    return {"ok": True}


# In-memory cache for covers (track_id -> {content: bytes, mime: str})
_COVER_CACHE = {}

@router.get("/cover/{track_id}")
async def track_cover(track_id: int):
    """Return the raw cover image (handles data URIs from DB with caching)."""
    if track_id in _COVER_CACHE:
        c = _COVER_CACHE[track_id]
        return Response(content=c["content"], media_type=c["mime"])

    cover_data = await get_track_cover(track_id)
    if not cover_data:
        raise HTTPException(404, "Cover not found")

    if cover_data.startswith("data:"):
        try:
            from fastapi.responses import Response
            import base64
            header, encoded = cover_data.split(",", 1)
            mime = header.split(":")[1].split(";")[0]
            data = base64.b64decode(encoded)
            
            # Cache it (limit cache size if needed, but for now 100 images)
            if len(_COVER_CACHE) > 200:
                _COVER_CACHE.clear() # Simple flush
            _COVER_CACHE[track_id] = {"content": data, "mime": mime}
            
            return Response(content=data, media_type=mime)
        except Exception:
            raise HTTPException(500, "Invalid cover data")

    return HTTPException(404, "Cover format not supported")



# ─── Lyrics ──────────────────────────────────────────────────────────────────

@router.get("/lyrics/{track_id}")
async def lyrics(track_id: int):
    track = await db.fetchone(
        "SELECT title, artist, duration FROM tracks WHERE id = ?", (track_id,)
    )
    if not track:
        raise HTTPException(404, "Track not found")
    if not track["title"]:
        return {"synced": None, "plain": None, "source": None}
    result = await get_lyrics(
        title    = track["title"],
        artist   = track["artist"] or "",
        duration = track["duration"] or 0,
    )
    return result


# ─── Discovery ───────────────────────────────────────────────────────────────

@router.get("/discover")
async def discover(device_id: str | None = Query(None)):
    return await get_discovery(device_id)


@router.get("/similar/{track_id}")
async def similar(track_id: int):
    return {"tracks": await get_similar(track_id)}


# ─── Play event ──────────────────────────────────────────────────────────────

@router.post("/play/{track_id}")
async def log_play(track_id: int, body: dict = None):
    device_id = (body or {}).get("device_id")
    await record_play(track_id, device_id)
    return {"ok": True}


@router.post("/track/{track_id}/like")
async def toggle_like(track_id: int, body: dict):
    is_fav = 1 if body.get("is_favorite") else 0
    await db.execute("UPDATE tracks SET is_favorite = ? WHERE id = ?", (is_fav, track_id))
    return {"ok": True, "is_favorite": is_fav}


# ─── Device registration ─────────────────────────────────────────────────────

@router.post("/device")
async def register_device(body: dict):
    device_id   = body.get("id")
    device_name = body.get("name", device_id)
    if not device_id:
        raise HTTPException(400, "Missing device id")
    await db.execute(
        "INSERT OR REPLACE INTO devices (id, name, last_seen) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (device_id, device_name),
    )
    return {"ok": True, "id": device_id}


# ─── Search ──────────────────────────────────────────────────────────────────

@router.get("/search")
async def search(q: str = Query(..., min_length=1)):
    q_like = f"%{q}%"
    tracks = await db.fetchall(
        """
        SELECT id, folder_id, path, filename, title, artist, album, duration,
               year, genre, track_num, is_favorite
        FROM tracks
        WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
        LIMIT 50
        """,
        (q_like, q_like, q_like),
    )
    return {"tracks": tracks, "query": q}
