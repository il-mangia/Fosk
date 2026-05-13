"""
All API routes for Fosk.
Mounted at /api by main.py.
"""
import base64
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, Query, Response, BackgroundTasks
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
ACTIVE_SCANS = 0


@router.get("/scan/status")
async def scan_status():
    return {"active_scans": ACTIVE_SCANS}


# ─── Setup & Authentication ──────────────────────────────────────────────────

@router.get("/setup/status")
async def setup_status():
    """Check if the server has been set up (i.e., if an admin exists)."""
    try:
        user = await db.fetchone("SELECT id FROM users LIMIT 1")
        return {"setup_done": user is not None}
    except Exception:
        # If the users table doesn't exist yet, setup is definitely not done
        return {"setup_done": False}


@router.get("/users")
async def list_users():
    """Return all users for the profile selection screen."""
    users = await db.fetchall("SELECT id, username, (password IS NOT NULL AND password != '') as has_password FROM users")
    return {"users": users}



async def run_scan_task(path: str):
    global ACTIVE_SCANS
    ACTIVE_SCANS += 1
    try:
        await scan_root(path)
    finally:
        ACTIVE_SCANS -= 1


@router.post("/setup")
async def complete_setup(body: dict, response: Response, background_tasks: BackgroundTasks):
    """
    Initial server setup: create admin and add initial music folders.
    Setup is now instant; scanning happens in the background.
    """
    username = body.get("username")
    password = body.get("password")
    folders  = body.get("folders", [])

    if not username or not password:
        raise HTTPException(400, "Username and password are required")

    # 1. Create admin user
    try:
        await db.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)",
            (username, password)
        )
    except Exception as e:
        raise HTTPException(400, f"Error creating user: {str(e)}")

    # 2. Set session cookie
    response.set_cookie(key="fosk_admin", value=username, httponly=True, samesite="lax", max_age=31536000)

    # 3. Queue scans in background
    for path in folders:
        if path.strip():
            background_tasks.add_task(run_scan_task, path.strip())

    return {"ok": True, "message": "Setup completed. Library scan started in background."}


@router.post("/login")
async def login(body: dict, response: Response):
    username = body.get("username")
    password = body.get("password") or ""
    
    user = await db.fetchone("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    if not user:
        raise HTTPException(401, "Credenziali non valide")
    
    if not user["is_enabled"]:
        raise HTTPException(403, "Account disabilitato")
    
    if user["expiry_date"]:
        from datetime import datetime
        if datetime.fromisoformat(user["expiry_date"]) < datetime.now():
            raise HTTPException(403, "Account scaduto")

    response.set_cookie(key="fosk_admin", value=username, httponly=True, samesite="lax", max_age=31536000)
    return {"ok": True, "username": username, "is_admin": bool(user["is_admin"])}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("fosk_admin")
    return {"ok": True}


# ─── Admin & Users ──────────────────────────────────────────────────────────

@router.get("/admin/users")
async def list_all_users(request: Request):
    # Basic check (should use a proper dependency but keeping it simple for now)
    admin_name = request.cookies.get("fosk_admin")
    admin = await db.fetchone("SELECT is_admin FROM users WHERE username = ?", (admin_name,))
    if not admin or not admin["is_admin"]:
        raise HTTPException(403, "Accesso negato")

    users = await db.fetchall("SELECT id, username, is_admin, is_enabled, expiry_date, avatar_url FROM users")
    return {"users": users}


@router.post("/admin/users/add")
async def add_user(body: dict, request: Request):
    admin_name = request.cookies.get("fosk_admin")
    admin = await db.fetchone("SELECT is_admin FROM users WHERE username = ?", (admin_name,))
    if not admin or not admin["is_admin"]:
        raise HTTPException(403, "Accesso negato")

    username = body.get("username")
    password = body.get("password", "")
    is_admin = 1 if body.get("is_admin") else 0
    expiry   = body.get("expiry_date")

    try:
        await db.execute(
            "INSERT INTO users (username, password, is_admin, expiry_date) VALUES (?, ?, ?, ?)",
            (username, password, is_admin, expiry)
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/admin/users/update")
async def update_user(body: dict, request: Request):
    admin_name = request.cookies.get("fosk_admin")
    admin = await db.fetchone("SELECT is_admin FROM users WHERE username = ?", (admin_name,))
    if not admin or not admin["is_admin"]:
        raise HTTPException(403, "Accesso negato")

    user_id = body.get("id")
    enabled = 1 if body.get("is_enabled") else 0
    expiry  = body.get("expiry_date")
    
    await db.execute(
        "UPDATE users SET is_enabled = ?, expiry_date = ? WHERE id = ?",
        (enabled, expiry, user_id)
    )
    return {"ok": True}


@router.post("/profile/avatar")
async def upload_avatar(request: Request):
    # This would normally use UploadFile, but for simplicity we'll assume base64 or similar for now
    # or just a placeholder. Let's implement real upload for premium feel.
    pass # Will implement properly if needed, for now just placeholder


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
async def scan_library(body: dict, background_tasks: BackgroundTasks):
    """
    Trigger a library scan in the background.
    Body: {"path": "/path/to/music"}
    """
    path = body.get("path")
    if not path:
        raise HTTPException(400, "Missing 'path' in body")
    
    background_tasks.add_task(run_scan_task, path)
    return {"ok": True, "message": f"Scan for {path} started in background."}


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


# ─── Playlists ───────────────────────────────────────────────────────────────

@router.get("/playlists")
async def list_playlists():
    return {"playlists": await db.fetchall("SELECT * FROM playlists ORDER BY name")}


@router.post("/playlists")
async def create_playlist(body: dict):
    name = body.get("name")
    if not name: raise HTTPException(400, "Missing name")
    pid = await db.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
    return {"id": pid, "name": name}


@router.get("/playlist/{pid}")
async def get_playlist(pid: int):
    playlist = await db.fetchone("SELECT * FROM playlists WHERE id = ?", (pid,))
    if not playlist: raise HTTPException(404)
    tracks = await db.fetchall(
        """
        SELECT t.* FROM tracks t
        JOIN playlist_tracks pt ON t.id = pt.track_id
        WHERE pt.playlist_id = ?
        ORDER BY pt.position
        """, (pid,)
    )
    return {"playlist": playlist, "tracks": tracks}


@router.post("/playlist/{pid}/add")
async def add_to_playlist(pid: int, body: dict):
    track_id = body.get("track_id")
    if not track_id: raise HTTPException(400)
    await db.execute(
        "INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id) VALUES (?, ?)",
        (pid, track_id)
    )
    return {"ok": True}


# ─── History ─────────────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(limit: int = 50):
    rows = await db.fetchall(
        """
        SELECT p.timestamp, t.* FROM plays p
        JOIN tracks t ON p.track_id = t.id
        ORDER BY p.timestamp DESC
        LIMIT ?
        """, (limit,)
    )
    return {"history": rows}
