"""
Recursive folder scanner.
Walks a root path, creates folder records and track records in the DB.
"""
import asyncio
from pathlib import Path

from config import AUDIO_EXTENSIONS
from database import db
from scanner.file_parser import parse_file
from services.deezer import enrich_track


async def _upsert_folder(path: Path, parent_id: int | None) -> int:
    existing = await db.fetchone("SELECT id FROM folders WHERE path = ?", (str(path),))
    if existing:
        return existing["id"]
    folder_id = await db.execute(
        "INSERT INTO folders (name, path, parent_id) VALUES (?, ?, ?)",
        (path.name, str(path), parent_id),
    )
    return folder_id


async def _upsert_track(folder_id: int, path: Path) -> None:
    existing = await db.fetchone("SELECT id FROM tracks WHERE path = ?", (str(path),))
    if existing:
        return  # already indexed

    meta = await asyncio.get_event_loop().run_in_executor(None, parse_file, path)

    # Enrichment: if cover or metadata is missing, try Deezer
    if not meta.get("cover_url") or not meta.get("artist") or not meta.get("album"):
        try:
            enriched = await enrich_track(meta)
            meta.update(enriched)
        except Exception as e:
            print(f"[Scanner] Enrichment failed for {path.name}: {e}")

    await db.execute(
        """
        INSERT INTO tracks
            (folder_id, path, filename, title, artist, album, duration,
             cover_url, year, genre, track_num)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            folder_id,
            str(path),
            path.name,
            meta.get("title"),
            meta.get("artist"),
            meta.get("album"),
            meta.get("duration"),
            meta.get("cover_url"),
            meta.get("year"),
            meta.get("genre"),
            meta.get("track_num"),
        ),
    )


async def scan_root(root: str) -> dict:
    """
    Entry point: scan a root music directory.
    Returns a summary dict with counts.
    """
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Path not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")

    folders_added = 0
    tracks_added  = 0

    async def _walk(path: Path, parent_id: int | None):
        nonlocal folders_added, tracks_added

        folder_id = await _upsert_folder(path, parent_id)
        folders_added += 1

        audio_files = [
            f for f in sorted(path.iterdir())
            if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
        ]
        
        # Parallelize track insertion for speed
        if audio_files:
            tasks = [_upsert_track(folder_id, f) for f in audio_files]
            await asyncio.gather(*tasks)
            tracks_added += len(audio_files)

        subdirs = sorted([d for d in path.iterdir() if d.is_dir()])
        for sub in subdirs:
            await _walk(sub, folder_id)

    await _walk(root_path, None)
    return {"folders": folders_added, "tracks": tracks_added, "root": str(root_path)}


async def get_all_folders() -> list[dict]:
    """Return all folders with an optional representative cover_url."""
    # We find the first track with a cover for each folder (or its subfolders)
    # This is a bit complex for a single query, so we'll do a simple version:
    # Get all folders, then for each, get one cover_url from its tracks.
    folders = await db.fetchall("SELECT * FROM folders ORDER BY name")
    
    # Enrich with a sample cover_id (we use ID because we have the /api/cover/{id} endpoint)
    # This query finds the first track id for each folder that has a cover_url
    covers = await db.fetchall("""
        SELECT folder_id, MIN(id) as track_id 
        FROM tracks 
        WHERE cover_url IS NOT NULL 
        GROUP BY folder_id
    """)
    cover_map = {c["folder_id"]: c["track_id"] for c in covers}
    
    result = []
    for f in folders:
        d = dict(f)
        d["representative_track_id"] = cover_map.get(f["id"])
        result.append(d)
    return result


async def get_folder(folder_id: int) -> dict | None:
    return await db.fetchone("SELECT * FROM folders WHERE id = ?", (folder_id,))


async def get_folder_tracks(folder_id: int) -> list[dict]:
    return await db.fetchall(
        """
        SELECT id, folder_id, path, filename, title, artist, album, duration,
               year, genre, track_num, is_favorite
        FROM tracks
        WHERE folder_id = ?
        ORDER BY track_num NULLS LAST, title
        """,
        (folder_id,),
    )


async def get_subtree_tracks(folder_id: int) -> list[dict]:
    """Return all tracks inside folder_id and every nested subfolder.
       Uses a Recursive CTE for maximum performance in SQLite."""
    return await db.fetchall(
        """
        WITH RECURSIVE subfolders(id) AS (
            SELECT ?
            UNION ALL
            SELECT f.id FROM folders f
            JOIN subfolders s ON f.parent_id = s.id
        )
        SELECT t.id, t.folder_id, t.path, t.filename, t.title, t.artist, t.album,
               t.duration, t.year, t.genre, t.track_num, t.is_favorite
        FROM tracks t
        WHERE t.folder_id IN (SELECT id FROM subfolders)
        ORDER BY t.album, t.track_num NULLS LAST, t.title
        """,
        (folder_id,),
    )


async def get_track_cover(track_id: int) -> str | None:
    row = await db.fetchone("SELECT cover_url FROM tracks WHERE id = ?", (track_id,))
    return row["cover_url"] if row else None


async def get_children_folders(folder_id: int) -> list[dict]:
    """Return direct children of a folder."""
    return await db.fetchall(
        "SELECT * FROM folders WHERE parent_id = ? ORDER BY name", (folder_id,)
    )
