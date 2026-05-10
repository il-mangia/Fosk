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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """Catch-all: serve index.html for the SPA."""
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
