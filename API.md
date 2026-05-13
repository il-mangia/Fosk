# 🔌 Fosk — API Reference

[🏠 Home](README.md) | [📦 Installation](INSTALL.md) | [🔌 API Reference](API.md)

---


Base URL: `http://<server-ip>:<port>`

All responses are JSON unless otherwise noted. Audio streaming returns binary data.

---

## Folders

### `GET /api/folders`

Returns all scanned folders.

**Response**
```json
[
  {
    "id": 1,
    "name": "Rock",
    "path": "/home/user/Music/Rock",
    "track_count": 42
  }
]
```

---

### `GET /api/folder/{id}`

Returns folder details and its tracks.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `id` | integer | Folder ID |

**Response**
```json
{
  "id": 1,
  "name": "Rock",
  "path": "/home/user/Music/Rock",
  "tracks": [
    {
      "id": 10,
      "title": "Bohemian Rhapsody",
      "artist": "Queen",
      "album": "A Night at the Opera",
      "duration": 354,
      "format": "mp3"
    }
  ]
}
```

---

### `POST /api/scan`

Starts a recursive scan of the given folder path.

**Request body**
```json
{ "path": "/home/user/Music" }
```

**Response**
```json
{ "status": "scanning", "path": "/home/user/Music" }
```

> Scanning runs asynchronously. Poll `/api/folders` to check when it completes.

---

## Tracks

### `GET /api/track/{id}`

Returns full metadata for a single track.

**Response**
```json
{
  "id": 10,
  "title": "Bohemian Rhapsody",
  "artist": "Queen",
  "album": "A Night at the Opera",
  "year": 1975,
  "genre": "Rock",
  "duration": 354,
  "format": "mp3",
  "cover_url": "https://...",
  "folder_id": 1
}
```

---

### `GET /api/stream/{id}`

Streams the audio file. Supports `Range` headers for seeking.

**Headers (optional)**

| Header | Example | Description |
|---|---|---|
| `Range` | `bytes=0-1023` | Byte range for partial content |

**Response** — `200 OK` or `206 Partial Content` with audio binary data.

---

### `GET /api/download/{id}`

Downloads the original audio file.

**Response** — File attachment with `Content-Disposition: attachment`.

---

## Lyrics

### `GET /api/lyrics/{id}`

Returns synced lyrics in LRC format, fetched from [lrclib.net](https://lrclib.net).

**Response**
```json
{
  "track_id": 10,
  "synced": true,
  "lrc": "[00:12.00] Is this the real life?\n[00:14.00] Is this just fantasy?"
}
```

Returns `null` for `lrc` if no lyrics are found.

---

## Discovery

### `GET /api/discover`

Returns track suggestions based on per-device play history.

**Query parameters**

| Name | Type | Description |
|---|---|---|
| `device_id` | string | Device identifier (from `POST /api/device`) |
| `limit` | integer | Max results (default: 10) |

**Response** — Array of track objects (same shape as `/api/track/{id}`).

---

### `GET /api/similar/{id}`

Returns tracks similar to the given track.

**Parameters**

| Name | Type | Description |
|---|---|---|
| `id` | integer | Source track ID |

**Response** — Array of track objects.

---

## Search

### `GET /api/search`

Full-text search across title, artist, and album.

**Query parameters**

| Name | Type | Description |
|---|---|---|
| `q` | string | Search query |

**Example**
```
GET /api/search?q=bohemian
```

**Response** — Array of track objects.

---

## Playback & Devices

### `POST /api/play/{id}`

Records a play event for a track. Used by the discovery engine.

**Request body**
```json
{ "device_id": "abc123" }
```

**Response**
```json
{ "status": "ok" }
```

---

### `POST /api/device`

Registers a new device and returns a unique device ID.

**Request body**
```json
{ "name": "Living Room TV" }
```

**Response**
```json
{ "device_id": "abc123", "name": "Living Room TV" }
```

---

## Error Responses

All errors follow this shape:

```json
{
  "detail": "Track not found"
}
```

| HTTP Code | Meaning |
|---|---|
| `404` | Resource not found |
| `422` | Invalid request parameters |
| `500` | Internal server error |
