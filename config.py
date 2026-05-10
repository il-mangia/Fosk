import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "fosk.db"

# Server settings
HOST = os.getenv("FOSK_HOST", "0.0.0.0")
PORT = int(os.getenv("FOSK_PORT", "8000"))

# Audio formats supported
AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wav", ".opus", ".wma", ".aiff"}

# External APIs
DEEZER_API_BASE = "https://api.deezer.com"
LRCLIB_API_BASE = "https://lrclib.net/api"   # Free lyrics API, no key needed

# Discovery weights (tunable)
DISCOVERY_NEVER_PLAYED_WEIGHT = 0.50
DISCOVERY_LOW_PLAYS_WEIGHT    = 0.25
DISCOVERY_RANDOM_WEIGHT       = 0.25

# Cache timeout in seconds for Deezer requests (in-memory, cleared on restart)
DEEZER_CACHE_TTL = 3600
