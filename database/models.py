"""
SQL schema definitions for Fosk.
Tables are created on first run.
"""

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS folders (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    path      TEXT NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES folders(id) ON DELETE CASCADE,
    scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id  INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
    path       TEXT NOT NULL UNIQUE,
    filename   TEXT NOT NULL,
    title      TEXT,
    artist     TEXT,
    album      TEXT,
    duration   REAL DEFAULT 0,
    cover_url  TEXT,
    year       INTEGER,
    genre      TEXT,
    track_num  INTEGER,
    is_favorite INTEGER DEFAULT 0,    -- 0 or 1
    added_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS devices (
    id        TEXT PRIMARY KEY,          -- UUID generated client-side
    name      TEXT NOT NULL,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plays (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id   INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    device_id  TEXT REFERENCES devices(id) ON DELETE SET NULL,
    timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tracks_folder  ON tracks(folder_id);
CREATE INDEX IF NOT EXISTS idx_tracks_sort    ON tracks(album, track_num, title);
CREATE INDEX IF NOT EXISTS idx_plays_track    ON plays(track_id);
CREATE INDEX IF NOT EXISTS idx_plays_device   ON plays(device_id);
CREATE INDEX IF NOT EXISTS idx_plays_ts       ON plays(timestamp);
"""
