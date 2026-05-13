# 🛠 Fosk — Installation Guide

[🏠 Home](README.md) | [📦 Installation](INSTALL.md) | [🔌 API Reference](API.md)

---


This guide covers installation on Linux, macOS, and Windows, plus optional steps for running Fosk as a background service.

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.9 or higher |
| pip | Latest recommended |

No other runtime dependencies are needed. Fosk uses SQLite (built into Python) and has no external database requirements.

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/il-mangia/fosk.git
cd fosk
```

Or download and extract the ZIP release from the releases page.

---

## Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Step 3 — Start the server

**Linux / macOS**

```bash
chmod +x start.sh
./start.sh              # port 8000 (default)
./start.sh 9000         # custom port
```

**Windows**

```bat
.\start.cmd
```


## Troubleshooting

**Port already in use**
```
ERROR: [Errno 98] Address already in use
```
Choose a different port: `./start.sh 9000`

---

**Python version too old**
```
SyntaxError: ...
```
Check your version with `python --version`. Fosk requires Python 3.9+.

---

**Lyrics or metadata not loading**

Fosk fetches lyrics from [lrclib.net](https://lrclib.net) and metadata from the public Deezer API. Both require internet access from the server machine. The metadata cache is in-memory and clears on restart.

---

**Tracks not appearing after scan**

Make sure the path you entered is correct and accessible by the user running Fosk. On Linux/macOS, verify permissions with `ls -la /your/music/path`.
