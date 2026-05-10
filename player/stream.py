"""
HTTP audio streaming with Range request support.
Allows browsers to seek within a track without re-downloading.
"""
import os
import mimetypes
from pathlib import Path
from fastapi import Request
from fastapi.responses import StreamingResponse, Response

# Ensure audio MIME types are registered
mimetypes.add_type("audio/flac",  ".flac")
mimetypes.add_type("audio/ogg",   ".ogg")
mimetypes.add_type("audio/opus",  ".opus")
mimetypes.add_type("audio/aac",   ".aac")
mimetypes.add_type("audio/x-m4a",".m4a")

CHUNK = 1024 * 256   # 256 KB chunks


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "audio/mpeg"


async def stream_file(path: Path, request: Request) -> Response:
    """
    Stream an audio file with Range header support.
    """
    if not path.exists():
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "File not found"}, status_code=404)

    file_size = path.stat().st_size
    mime      = _guess_mime(path)
    range_hdr = request.headers.get("range")

    if range_hdr:
        # Parse "bytes=start-end"
        try:
            byte_range = range_hdr.replace("bytes=", "").strip()
            parts      = byte_range.split("-")
            start      = int(parts[0]) if parts[0] else 0
            end        = int(parts[1]) if parts[1] else file_size - 1
        except (ValueError, IndexError):
            start, end = 0, file_size - 1

        end = min(end, file_size - 1)
        length = end - start + 1

        async def _iter():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(CHUNK, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            "Content-Range":  f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges":  "bytes",
            "Content-Length": str(length),
            "Content-Type":   mime,
        }
        return StreamingResponse(_iter(), status_code=206, headers=headers)

    # Full file response
    async def _iter_full():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                yield chunk

    headers = {
        "Accept-Ranges":  "bytes",
        "Content-Length": str(file_size),
        "Content-Type":   mime,
    }
    return StreamingResponse(_iter_full(), status_code=200, headers=headers)
