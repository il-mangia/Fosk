<p align="center">
  <img src="frontend/Logo.png" width="128" alt="Fosk Logo">
</p>

# Fosk — Personal Music Server

[🏠 Home](README.md) | [📦 Installation](INSTALL.md) | [🔌 API Reference](API.md)

---

> Self-hosted music streaming for your home network. Your library, your rules.

### 📖 Documentation
- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📁 First Scan](#-first-scan)
- [🏗 Project Structure](#-project-structure)
- [⚙️ Configuration](#️-configuration)
- [📝 Technical Notes](#-technical-notes)


Fosk scans your local music folders and makes them available for streaming to any device on your LAN — with metadata enrichment, synced lyrics, smart discovery, and a clean dark UI.

---

## ✨ Features

| Feature | Status |
|---|---|
| Recursive folder scanning | ✅ |
| ID3 metadata (MP3, FLAC, M4A, OGG) | ✅ |
| Filename fallback parser | ✅ |
| Metadata enrichment via Deezer | ✅ |
| Synced lyrics (LRC) via lrclib.net | ✅ |
| HTTP streaming with Range support | ✅ |
| Track download | ✅ |
| Per-device smart discovery | ✅ |
| Per-device play history | ✅ |
| Modern dark UI | ✅ |
| Live search | ✅ |
| Shuffle / Repeat | ✅ |

**Supported formats:** MP3 · FLAC · OGG · M4A · AAC · WAV · OPUS · WMA · AIFF

---

## 🚀 Quick Start

### Method 1 — Automatic script

```bash
chmod +x start.sh
./start.sh           # default port 8000
./start.sh 9000      # custom port
```

### Method 2 — Manual

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open your browser:

- **LAN:** `http://<server-ip>:8000`
- **Local:** `http://localhost:8000`

---

## 📁 First Scan

1. Open the app in your browser
2. On the **Home** page, enter the path to your music folder:
   - Windows: `D:\Music`
   - Linux/macOS: `/home/user/Music`
3. Click **Scan**
4. Wait for completion — folders appear in the sidebar automatically

---

## 🏗 Project Structure

```
fosk/
├── main.py              ← FastAPI entry point
├── config.py            ← Global configuration
├── requirements.txt
├── start.sh             ← Launch script
│
├── database/
│   ├── db.py            ← aiosqlite connection
│   └── models.py        ← SQL schema
│
├── scanner/
│   ├── folder_scan.py   ← Recursive folder scanning
│   └── file_parser.py   ← ID3/Vorbis/MP4 tag reader
│
├── services/
│   ├── deezer.py        ← Deezer API (metadata enrichment)
│   ├── lyrics.py        ← lrclib.net API (synced LRC lyrics)
│   └── discovery.py     ← Recommendation engine
│
├── player/
│   └── stream.py        ← HTTP streaming with Range support
│
├── api/
│   └── routes.py        ← All REST endpoints
│
└── frontend/
    ├── index.html       ← SPA shell
    ├── style.css        ← Dark UI styles
    └── app.js           ← Frontend logic
```

---

## 🔌 API

See [API.md](./API.md) for the full endpoint reference.

---

## ⚙️ Configuration

Fosk can be configured via environment variables:

| Variable | Default | Description |
|---|---|---|
| `FOSK_HOST` | `0.0.0.0` | Bind address |
| `FOSK_PORT` | `8000` | Listening port |

---

## 📝 Technical Notes

- **Lyrics** — Powered by [lrclib.net](https://lrclib.net): free, no API key required
- **Metadata** — Uses the public Deezer API: no API key, in-memory cache (clears on restart)
- **Database** — `fosk.db` SQLite file created in the project root
- **Files** — Audio files are never copied or moved; only file paths are stored in the database
- **Privacy** — Everything runs locally on your machine; no data leaves your network

---

## 📄 Documentation

- [INSTALL.md](./INSTALL.md) — Full installation guide
- [API.md](./API.md) — REST API reference

---

## 📜 License

MIT — do whatever you want with it.
