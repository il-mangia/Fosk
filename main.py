"""
Fosk — Personal Music Server
Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from database.db import init_db, close_db
from api.routes  import router
from config      import HOST, PORT


async def get_public_ip():
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            res = await client.get("https://api.ipify.org", timeout=2.0)
            return res.text
    except Exception:
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    # Show Banner
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    public_ip = await get_public_ip()
    
    print("\n" + "="*50)
    print(f" 🎵 Fosk Music Server is RUNNING")
    print("="*50)
    print(f" LAN:    http://{local_ip}:{PORT}")
    if public_ip:
        print(f" PUBLIC: http://{public_ip}:{PORT} (if port-forwarded)")
    print("="*50 + "\n")
    
    yield
    await close_db()


app = FastAPI(
    title="Fosk",
    description="Personal Music Server",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins (needed for LAN access from any device)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router, prefix="/api")

# Static frontend files
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_portal():
    """Entry point: Login and Setup portal."""
    return FileResponse(FRONTEND_DIR / "fosk.html")


@app.get("/app", include_in_schema=False)
async def serve_app():
    """Main music player application."""
    return FileResponse(FRONTEND_DIR / "app.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_fallback(full_path: str):
    """Fallback to portal for unknown routes."""
    # If the path looks like a file that should be in /static, but wasn't caught,
    # we don't want to return HTML. But uvicorn/fastapi handles /static mount first.
    return FileResponse(FRONTEND_DIR / "fosk.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
