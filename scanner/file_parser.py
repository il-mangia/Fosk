"""
Parse audio file metadata using mutagen.
Falls back to filename parsing when tags are missing.
"""
import re
from pathlib import Path
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp4 import MP4Cover
import base64


# Patterns to strip track numbers / noise from filenames
_STRIP_PATTERNS = [
    r"^\d{1,3}[\s.\-_]+",        # leading track number  "01 - " / "02."
    r"\s*[\(\[]\d{4}[\)\]]",     # year in brackets "(2020)"
    r"\s*[\(\[].*?[\)\]]",       # anything in brackets
    r"\.(mp3|flac|ogg|m4a|aac|wav|opus|wma|aiff)$",  # extension
]


def _clean_filename(name: str) -> str:
    result = name
    for pat in _STRIP_PATTERNS:
        result = re.sub(pat, "", result, flags=re.IGNORECASE).strip()
    return result or name  # never return empty string


def _embed_cover(tag_data: bytes, mime: str = "image/jpeg") -> str:
    """Return a data-URI from raw cover bytes."""
    b64 = base64.b64encode(tag_data).decode()
    return f"data:{mime};base64,{b64}"


def parse_file(path: Path) -> dict:
    """
    Extract metadata from an audio file.
    Returns a dict with: title, artist, album, duration, cover_url, year, genre, track_num.
    All values may be None.
    """
    meta = {
        "title": None,
        "artist": None,
        "album": None,
        "duration": 0.0,
        "cover_url": None,
        "year": None,
        "genre": None,
        "track_num": None,
    }

    try:
        audio = MutagenFile(path, easy=False)
        if audio is None:
            raise ValueError("mutagen returned None")

        # Duration
        if audio.info:
            meta["duration"] = round(audio.info.length, 2)

        suffix = path.suffix.lower()

        # ── MP3 / ID3 ──────────────────────────────────────────────────────
        if suffix == ".mp3":
            from mutagen.id3 import ID3
            try:
                tags = ID3(path)
                def _id3(key):
                    frame = tags.get(key)
                    return str(frame) if frame else None

                meta["title"]     = _id3("TIT2")
                meta["artist"]    = _id3("TPE1")
                meta["album"]     = _id3("TALB")
                meta["genre"]     = _id3("TCON")
                yr = _id3("TDRC") or _id3("TYER")
                meta["year"]      = int(str(yr)[:4]) if yr else None
                trck = _id3("TRCK")
                if trck:
                    meta["track_num"] = int(trck.split("/")[0])

                # Cover
                for tag in tags.values():
                    if tag.FrameID == "APIC":
                        meta["cover_url"] = _embed_cover(tag.data, tag.mime)
                        break
            except ID3NoHeaderError:
                pass

        # ── FLAC ──────────────────────────────────────────────────────────
        elif suffix == ".flac":
            from mutagen.flac import FLAC
            flac = FLAC(path)
            def _vc(key):
                vals = flac.get(key)
                return vals[0] if vals else None

            meta["title"]     = _vc("title")
            meta["artist"]    = _vc("artist")
            meta["album"]     = _vc("album")
            meta["genre"]     = _vc("genre")
            meta["year"]      = int(_vc("date")[:4]) if _vc("date") else None
            trck = _vc("tracknumber")
            if trck:
                meta["track_num"] = int(trck.split("/")[0])
            if flac.pictures:
                pic = flac.pictures[0]
                meta["cover_url"] = _embed_cover(pic.data, pic.mime)

        # ── M4A / AAC ─────────────────────────────────────────────────────
        elif suffix in (".m4a", ".aac", ".mp4"):
            from mutagen.mp4 import MP4
            mp4 = MP4(path)
            def _mp4(key):
                vals = mp4.tags.get(key) if mp4.tags else None
                return str(vals[0]) if vals else None

            meta["title"]     = _mp4("©nam")
            meta["artist"]    = _mp4("©ART")
            meta["album"]     = _mp4("©alb")
            meta["genre"]     = _mp4("©gen")
            yr = _mp4("©day")
            meta["year"]      = int(yr[:4]) if yr else None
            trck = mp4.tags.get("trkn") if mp4.tags else None
            if trck:
                meta["track_num"] = trck[0][0]
            covers = mp4.tags.get("covr") if mp4.tags else None
            if covers:
                cover = covers[0]
                mime = "image/jpeg" if cover.imageformat == MP4Cover.FORMAT_JPEG else "image/png"
                meta["cover_url"] = _embed_cover(bytes(cover), mime)

        # ── OGG / Vorbis ──────────────────────────────────────────────────
        elif suffix in (".ogg", ".opus"):
            from mutagen.oggvorbis import OggVorbis
            ogg = OggVorbis(path)
            def _vb(key):
                vals = ogg.get(key)
                return vals[0] if vals else None
            meta["title"]  = _vb("title")
            meta["artist"] = _vb("artist")
            meta["album"]  = _vb("album")
            meta["genre"]  = _vb("genre")
            yr = _vb("date")
            meta["year"] = int(yr[:4]) if yr else None

    except Exception as e:
        # Non-fatal: we fall back to filename parsing
        print(f"[Parser] Warning for {path.name}: {e}")

    # ── Fallback: derive title/artist from filename ─────────────────────
    if not meta["title"]:
        stem = path.stem
        # "Artist - Title" pattern
        if " - " in stem:
            parts = stem.split(" - ", 1)
            cleaned_left  = _clean_filename(parts[0])
            cleaned_right = _clean_filename(parts[1])
            if not meta["artist"]:
                meta["artist"] = cleaned_left
            meta["title"] = cleaned_right
        else:
            meta["title"] = _clean_filename(stem)

    return meta
