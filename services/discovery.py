"""
Discovery engine — suggests music from the local library based on:
  - never-played tracks
  - rarely-played tracks
  - similar genre/artist
  - per-device listening history
"""
import random
from database import db


async def get_discovery(device_id: str | None, limit: int = 30) -> dict:
    """
    Returns discovery sections: forgotten, hidden_gems, random_pick.
    """
    all_tracks = await db.fetchall("SELECT * FROM tracks")
    if not all_tracks:
        return {"forgotten": [], "hidden_gems": [], "random_pick": []}

    track_ids = [t["id"] for t in all_tracks]

    # Play counts per track (globally and per device)
    global_counts = await _play_counts(track_ids)
    device_counts = await _play_counts(track_ids, device_id) if device_id else {}

    never_played_globally = [t for t in all_tracks if global_counts.get(t["id"], 0) == 0]
    never_played_device   = [t for t in all_tracks if device_counts.get(t["id"], 0) == 0]

    # Rarely played: played ≥1 but ≤3 times globally
    rarely_played = [
        t for t in all_tracks
        if 1 <= global_counts.get(t["id"], 0) <= 3
    ]

    # Forgotten: played at least once but not in last 30 days
    forgotten_ids = await _forgotten_track_ids()
    forgotten = [t for t in all_tracks if t["id"] in forgotten_ids]

    # Hidden gems: never played on this device but played globally
    if device_id:
        hidden = [
            t for t in all_tracks
            if device_counts.get(t["id"], 0) == 0 and global_counts.get(t["id"], 0) > 0
        ]
    else:
        hidden = rarely_played

    # Random picks from never-played-on-device pool
    pool = never_played_device or never_played_globally or all_tracks
    random_picks = random.sample(pool, min(limit // 3, len(pool)))

    # Recently added: last 15 tracks indexed
    recently_added = sorted(all_tracks, key=lambda x: x.get("added_at", ""), reverse=True)[:15]

    def _fmt(tracks, n):
        random.shuffle(tracks)
        return _serialize(tracks[:n])

    return {
        "forgotten":      _fmt(forgotten or never_played_globally, 15),
        "hidden_gems":    _fmt(hidden, 15),
        "random_pick":    _serialize(random_picks[:10]),
        "recently_added": _serialize(recently_added),
    }


async def get_similar(track_id: int, limit: int = 10) -> list[dict]:
    """
    Find tracks similar to track_id by matching artist or genre.
    """
    track = await db.fetchone("SELECT * FROM tracks WHERE id = ?", (track_id,))
    if not track:
        return []

    similar = []

    # Same artist, different track
    if track["artist"]:
        rows = await db.fetchall(
            "SELECT * FROM tracks WHERE artist = ? AND id != ? ORDER BY RANDOM() LIMIT ?",
            (track["artist"], track_id, limit),
        )
        similar.extend(rows)

    # Same genre
    if track["genre"] and len(similar) < limit:
        rows = await db.fetchall(
            """
            SELECT * FROM tracks
            WHERE genre = ? AND id != ? AND artist != ?
            ORDER BY RANDOM() LIMIT ?
            """,
            (track["genre"], track_id, track.get("artist", ""), limit - len(similar)),
        )
        similar.extend(rows)

    # Pad with random
    if len(similar) < limit:
        rows = await db.fetchall(
            "SELECT * FROM tracks WHERE id != ? ORDER BY RANDOM() LIMIT ?",
            (track_id, limit - len(similar)),
        )
        for r in rows:
            if r["id"] not in {s["id"] for s in similar}:
                similar.append(r)

    return _serialize(similar[:limit])


async def record_play(track_id: int, device_id: str | None) -> None:
    if device_id:
        await db.execute(
            "INSERT OR IGNORE INTO devices (id, name) VALUES (?, ?)",
            (device_id, device_id),
        )
        await db.execute(
            "UPDATE devices SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
            (device_id,),
        )
    await db.execute(
        "INSERT INTO plays (track_id, device_id) VALUES (?, ?)",
        (track_id, device_id),
    )


# ─── internal helpers ────────────────────────────────────────────────────────

async def _play_counts(track_ids: list[int], device_id: str | None = None) -> dict[int, int]:
    if not track_ids:
        return {}
    placeholders = ",".join("?" * len(track_ids))
    if device_id:
        rows = await db.fetchall(
            f"""
            SELECT track_id, COUNT(*) as cnt FROM plays
            WHERE track_id IN ({placeholders}) AND device_id = ?
            GROUP BY track_id
            """,
            (*track_ids, device_id),
        )
    else:
        rows = await db.fetchall(
            f"""
            SELECT track_id, COUNT(*) as cnt FROM plays
            WHERE track_id IN ({placeholders})
            GROUP BY track_id
            """,
            tuple(track_ids),
        )
    return {r["track_id"]: r["cnt"] for r in rows}


async def _forgotten_track_ids() -> set[int]:
    rows = await db.fetchall(
        """
        SELECT DISTINCT track_id FROM plays
        WHERE timestamp < datetime('now', '-30 days')
        AND track_id NOT IN (
            SELECT DISTINCT track_id FROM plays
            WHERE timestamp >= datetime('now', '-30 days')
        )
        """
    )
    return {r["track_id"] for r in rows}


def _serialize(tracks: list[dict]) -> list[dict]:
    return [
        {
            "id":       t["id"],
            "title":    t["title"] or t["filename"],
            "artist":   t["artist"],
            "album":    t["album"],
            "duration": t["duration"],
            "cover_url":t["cover_url"],
            "genre":    t["genre"],
            "folder_id":t["folder_id"],
        }
        for t in tracks
    ]
