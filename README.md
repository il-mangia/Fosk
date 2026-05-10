# 🎵 Fosk — Personal Music Server

Un server musicale personale self-hosted per casa tua!  
Accedi alla tua musica locale da qualsiasi dispositivo in LAN.

---

## ✨ Funzionalità

| Feature | Stato |
|---|---|
| Scansione ricorsiva cartelle | ✅ |
| Metadati ID3 (MP3, FLAC, M4A, OGG) | ✅ |
| Parsing da nome file come fallback | ✅ |
| Enrichment metadati via Deezer | ✅ |
| Testi sincronizzati (LRC) via lrclib.net | ✅ |
| Streaming HTTP con Range support | ✅ |
| Download brani | ✅ |
| Discovery intelligente per dispositivo | ✅ |
| Cronologia play separata per device | ✅ |
| Interfaccia dark moderna | ✅ |
| Ricerca live | ✅ |
| Shuffle / Repeat | ✅ |

---

## 🚀 Avvio rapido

### Metodo 1 — Script automatico
```bash
chmod +x start.sh
./start.sh          # porta 8000 (default)
./start.sh 9000     # porta personalizzata
```

### Metodo 2 — Manuale
```bash
# Installa dipendenze
pip install -r requirements.txt

# Avvia server
uvicorn main:app --host 0.0.0.0 --port 8000
```

Poi apri il browser su:
- **LAN**: `http://<ip-server>:8000`
- **Locale**: `http://localhost:8000`

---

## 📁 Prima scansione

1. Apri l'app nel browser
2. Nella **Home**, inserisci il percorso della cartella musicale:
   - Windows: `D:\Musica`  
   - Linux/Mac: `/home/user/Musica`
3. Clicca **Scansiona**
4. Attendi il completamento → le cartelle appaiono nella sidebar

---

## 🏗 Struttura progetto

```
fosk/
├── main.py              ← Entry point FastAPI
├── config.py            ← Configurazione globale
├── requirements.txt
├── start.sh             ← Script avvio
│
├── database/
│   ├── db.py            ← Connessione aiosqlite
│   └── models.py        ← Schema SQL
│
├── scanner/
│   ├── folder_scan.py   ← Scansione ricorsiva
│   └── file_parser.py   ← Lettura tag ID3/Vorbis/MP4
│
├── services/
│   ├── deezer.py        ← API Deezer (metadata)
│   ├── lyrics.py        ← API lrclib.net (testi LRC)
│   └── discovery.py     ← Motore suggerimenti
│
├── player/
│   └── stream.py        ← HTTP streaming con Range
│
├── api/
│   └── routes.py        ← Tutti gli endpoint REST
│
└── frontend/
    ├── index.html       ← SPA shell
    ├── style.css        ← UI dark
    └── app.js           ← Logica frontend
```

---

## 🔌 API endpoints

| Metodo | Path | Descrizione |
|---|---|---|
| `GET` | `/api/folders` | Lista cartelle |
| `GET` | `/api/folder/{id}` | Dettaglio + brani cartella |
| `POST` | `/api/scan` | Avvia scansione `{"path":"..."}` |
| `GET` | `/api/track/{id}` | Dettaglio brano |
| `GET` | `/api/stream/{id}` | Stream audio (Range support) |
| `GET` | `/api/download/{id}` | Download file originale |
| `GET` | `/api/lyrics/{id}` | Testi sincronizzati |
| `GET` | `/api/discover` | Suggerimenti discovery |
| `GET` | `/api/similar/{id}` | Brani simili |
| `GET` | `/api/search?q=...` | Ricerca full-text |
| `POST` | `/api/play/{id}` | Registra play `{"device_id":"..."}` |
| `POST` | `/api/device` | Registra dispositivo |

---

## ⚙️ Configurazione avanzata

Variabili d'ambiente:
```bash
FOSK_HOST=0.0.0.0   # bind address
FOSK_PORT=8000       # porta
```

---

## 📝 Note tecniche

- **Testi**: usa [lrclib.net](https://lrclib.net) — gratuito, no API key
- **Metadata**: Deezer API pubblica — no API key, cache in-memory (si svuota al riavvio)
- **Database**: `fosk.db` nella cartella del progetto (SQLite)
- **File audio**: non vengono mai copiati, solo i percorsi sono salvati nel DB
- **Formati supportati**: MP3, FLAC, OGG, M4A, AAC, WAV, OPUS, WMA, AIFF
