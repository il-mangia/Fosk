"""
Async SQLite database layer using aiosqlite.
Provides a single shared connection pool via get_db().
"""
import aiosqlite
from pathlib import Path
from config import DB_PATH
from database.models import SCHEMA

_db: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Create tables if they don't exist."""
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    # High performance settings
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA synchronous=OFF")
    await _db.execute("PRAGMA cache_size=-64000") # 64MB cache
    await _db.executescript(SCHEMA)
    await _db.commit()
    print(f"[DB] Database ready at {DB_PATH}")


async def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _db


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None


# ─── helpers ─────────────────────────────────────────────────────────────────

async def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    db = await get_db()
    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def fetchone(sql: str, params: tuple = ()) -> dict | None:
    db = await get_db()
    async with db.execute(sql, params) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def execute(sql: str, params: tuple = ()) -> int:
    """Execute INSERT/UPDATE/DELETE. Returns lastrowid."""
    db = await get_db()
    async with db.execute(sql, params) as cur:
        await db.commit()
        return cur.lastrowid
