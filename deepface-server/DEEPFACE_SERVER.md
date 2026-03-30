# DeepFace Server — Integration Reference

A self-hosted HTTP API for face detection, recognition, and real-time RTSP stream processing. Built on DeepFace v0.0.99 with Buffalo_L embeddings stored in PostgreSQL + pgvector.

---

## Architecture Overview

```
Client / Integrating App
        │
        ▼
FastAPI (app/main.py)           ← single uvicorn worker (DeepFace is not thread-safe)
        │
        ├── app/routes.py       ← HTTP endpoints
        ├── app/stream.py       ← RTSP stream processors (asyncio Tasks)
        ├── app/config.py       ← pydantic-settings, env vars
        ├── app/schemas.py      ← Pydantic request/response models
        └── app/utils.py        ← image I/O helpers
        │
        ▼
DeepFace.search / register / represent / extract_faces
        │
        ▼
PostgreSQL + pgvector            ← face embeddings stored as 512-dim vectors
```

**Critical constraint: always run with `workers=1`.** DeepFace's in-process model cache is not thread-safe. Multiple workers each load their own model copy and maintain separate caches — this causes silent cross-worker mismatch on concurrent requests.

---

## Model Stack

| Component | Value | Notes |
|-----------|-------|-------|
| Recognition model | `Buffalo_L` | InsightFace ArcFace-based, 512-dim cosine embeddings |
| Face detector | `mtcnn` | Reliable across angles; retinaface had broken weight downloads |
| Distance metric | `cosine` | Threshold 0.40 (tightened from DeepFace default 0.55) |
| normalization | `"raw"` | **Critical** — see section below |
| l2_normalize | `False` | Must be consistent across all register/search calls |

### The normalization="raw" requirement

Buffalo_L (InsightFace) internally calls `cv2.dnn.blobFromImages(mean=127.5, std=127.5)` which expects pixel values in **[0, 255]**.

DeepFace's `normalization="base"` (the default) is a no-op — it leaves the image at [0, 1] after its own internal rescaling. This causes InsightFace to receive ~0.0 pixels, producing near-identical embeddings for every face (all distances collapse to ~0.001).

`normalization="raw"` multiplies the [0,1] image by 255 before passing it to InsightFace, which is the correct path.

**Rule: every call to `DeepFace.register`, `DeepFace.search`, and `DeepFace.represent` must pass `normalization="raw"` and `l2_normalize=False`.** These two flags are stored in the database alongside each embedding and used as SQL filter predicates — mixing them silently queries the wrong row set.

---

## Configuration

All settings are in `app/config.py` via pydantic-settings. Override with environment variables or a `.env` file.

| Env var | Default | Description |
|---------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Listen port |
| `WORKERS` | `1` | Uvicorn workers — keep at 1 |
| `MODEL_NAME` | `Buffalo_L` | DeepFace model name |
| `DETECTOR_BACKEND` | `mtcnn` | Face detector backend |
| `DISTANCE_METRIC` | `cosine` | Distance function |
| `COSINE_THRESHOLD` | `0.40` | Match threshold (lower = stricter) |
| `DEEPFACE_POSTGRES_URI` | `postgresql://deepface:deepface@localhost:5432/deepface` | pgvector connection string |

**Important**: `app/config.py` sets `TF_USE_LEGACY_KERAS=1` at module level. This **must** happen before any TensorFlow import. The import order in `app/main.py` is intentional — `app.config` is imported first.

---

## HTTP API Reference

Base URL: `http://localhost:8000`

All image endpoints accept two input formats:
- **Multipart** (`Content-Type: multipart/form-data`): `file` field as binary upload
- **JSON** (`Content-Type: application/json`): `image` field as raw base64 or data-URI

### GET /health

Returns server status and active configuration.

```json
{
  "status": "ok",
  "model_name": "Buffalo_L",
  "detector_backend": "mtcnn",
  "database": "localhost:5432/deepface"
}
```

---

### POST /detect

Detect all faces in an image. Returns bounding boxes and base64 PNG face crops.

**Request (JSON):**
```json
{
  "image": "<base64>",
  "enforce_detection": true
}
```

**Response:**
```json
{
  "faces_detected": 2,
  "faces": [
    {
      "facial_area": { "x": 100, "y": 50, "w": 200, "h": 250, "left_eye": [150, 120], "right_eye": [250, 120] },
      "confidence": 0.9998,
      "face_base64": "<base64 PNG crop>"
    }
  ]
}
```

---

### POST /represent

Compute 512-dim Buffalo_L embeddings for every face in the image.

**Request (JSON):**
```json
{
  "image": "<base64>",
  "enforce_detection": true
}
```

**Response:**
```json
{
  "model_name": "Buffalo_L",
  "embeddings": [
    {
      "embedding": [0.123, -0.456, ...],
      "facial_area": { "x": 100, "y": 50, "w": 200, "h": 250 },
      "face_confidence": 0.9998
    }
  ]
}
```

---

### POST /register

Register a face into the pgvector database under an identity label.

**Request (JSON):**
```json
{
  "image": "<base64>",
  "img_name": "alice",
  "enforce_detection": true
}
```

**Request (multipart):**
```
file=<binary>
img_name=alice
enforce_detection=true
```

**Response:**
```json
{
  "inserted": 1,
  "img_name": "alice"
}
```

`inserted: 0` means a duplicate face hash was detected — the face is already registered. This is expected and correct behavior.

---

### POST /search

Search the database for registered faces matching the query image. Returns one result group per detected face in the query image.

**Request (JSON):**
```json
{
  "image": "<base64>",
  "enforce_detection": true,
  "search_method": "exact",
  "similarity_search": false,
  "k": null
}
```

**Parameters:**
- `search_method`: `"exact"` (precise cosine scan) or `"ann"` (approximate, requires `/build-index` first)
- `similarity_search`: if `true`, returns similarity score instead of distance
- `k`: limit results per face group (null = return all matches under threshold)

**Response:**
```json
{
  "results": [
    {
      "matches": [
        {
          "img_name": "alice",
          "distance": 0.312,
          "confidence": 68.8,
          "threshold": 0.40,
          "distance_metric": "cosine",
          "source_x": 0, "source_y": 0, "source_w": 640, "source_h": 480,
          "target_x": 100, "target_y": 50, "target_w": 200, "target_h": 250
        }
      ]
    }
  ]
}
```

`results` has one entry per face detected in the query image. An entry with `matches: []` means a face was detected but no registered match was found under the threshold.

**Distance interpretation (cosine, Buffalo_L, normalization="raw"):**
- `0.0` — identical image
- `0.30–0.45` — same person, different photo
- `> 0.40` (threshold) — no match returned

---

### POST /build-index

Build an ANN (approximate nearest-neighbor) index on the pgvector database for faster search at scale. Required before using `search_method="ann"`.

```json
{ "status": "ok", "message": "ANN index built successfully for model 'Buffalo_L'." }
```

Returns 422 if the database has no registered faces.

---

## RTSP Stream Processing

The server can monitor one or more RTSP streams continuously, running face recognition on sampled frames and delivering matches to a webhook.

### Architecture

Each stream runs as an asyncio `Task` (`app/stream.py`). The global `_streams` dict maps `stream_id → StreamProcessor`. Blocking operations (cv2, DeepFace) run in the default thread executor via `loop.run_in_executor()`.

**Frame freshness fix:** OpenCV buffers RTSP frames internally. During `asyncio.sleep(interval)`, frames accumulate in the buffer. A naive `cap.read()` returns the oldest buffered frame. The server drains the buffer by calling `cap.grab()` up to 30 times (≈1 second at 30fps), then calls `cap.retrieve()` to decode only the latest frame.

**Recommended ffmpeg encoding:** Use MJPEG (`-c:v mjpeg`) instead of H264 for RTSP sources. H264 is inter-frame encoded — skipping frames during buffer drain breaks the P/B-frame reference chain and produces decoder warnings. MJPEG is fully intra-frame; every frame is independent.

```bash
# Push webcam to MediaMTX as MJPEG
ffmpeg -f avfoundation -framerate 30 -i "0" \
  -c:v mjpeg -q:v 3 \
  -f rtsp rtsp://localhost:8554/webcam_stream
```

### POST /stream/start

```json
{
  "rtsp_url": "rtsp://localhost:8554/webcam_stream",
  "interval_seconds": 2.0,
  "webhook_url": "http://your-service/webhook",
  "stream_id": "cam-01"
}
```

- `stream_id` is optional — auto-generated as an 8-char UUID prefix if omitted
- `interval_seconds` controls how often a frame is sampled and processed
- Returns 409 if a stream with that ID is already running

**Response:**
```json
{
  "stream_id": "cam-01",
  "status": "running",
  "rtsp_url": "rtsp://localhost:8554/webcam_stream",
  "interval_seconds": 2.0,
  "webhook_url": "http://your-service/webhook"
}
```

### POST /stream/stop/{stream_id}

Cancels the asyncio Task, releases the cv2 capture, and removes the stream from the registry.

```json
{ "stream_id": "cam-01", "status": "stopped" }
```

### GET /stream/status

Lists all active stream processors.

```json
{
  "streams": [
    {
      "stream_id": "cam-01",
      "rtsp_url": "rtsp://localhost:8554/webcam_stream",
      "status": "running",
      "interval_seconds": 2.0,
      "webhook_url": "http://your-service/webhook",
      "frames_processed": 143,
      "started_at": "2026-03-30T00:30:00+00:00",
      "last_error": null
    }
  ]
}
```

`status` values: `"running"` | `"stopped"` | `"error"` (crashed with unrecoverable exception)

### Webhook Payload

The server POSTs JSON to `webhook_url` whenever a registered face is matched. No webhook is fired if a frame has no face or no match passes the threshold.

```json
{
  "stream_id": "cam-01",
  "rtsp_url": "rtsp://localhost:8554/webcam_stream",
  "timestamp": "2026-03-30T00:45:49.412Z",
  "frames_processed": 42,
  "faces_found": 1,
  "matches": [
    {
      "img_name": "alice",
      "distance": 0.312,
      "confidence": 68.8,
      "threshold": 0.40,
      "facial_area": { "x": 100, "y": 50, "w": 200, "h": 250 }
    }
  ]
}
```

`matches` contains one entry per recognized face in the frame. Multiple faces in one frame → multiple entries in `matches`. Webhook delivery timeout is 5 seconds; failures are logged as warnings and do not crash the stream.

---

## Database Schema

DeepFace manages the schema automatically. The relevant table is `face_embeddings` (created by DeepFace on first register):

| Column | Type | Notes |
|--------|------|-------|
| `img_name` | text | Identity label passed to `/register` |
| `embedding` | vector(512) | Buffalo_L face embedding |
| `model_name` | text | `"Buffalo_L"` |
| `detector_backend` | text | `"mtcnn"` |
| `aligned` | bool | Always `true` in this server |
| `l2_normalized` | bool | `false` in this server |

DeepFace filters by `(model_name, detector_backend, aligned, l2_normalized)` when searching — **not** by normalization. This means registrations made with different `normalization` values (e.g. `"base"` vs `"raw"`) share the same rows but produce incompatible vectors. Always use consistent settings across all calls.

To clear the database between normalization changes:
```sql
TRUNCATE face_embeddings;
```

---

## Infrastructure Setup

### PostgreSQL with pgvector

```bash
docker run -d --name deepface-postgres \
  -e POSTGRES_USER=deepface \
  -e POSTGRES_PASSWORD=deepface \
  -e POSTGRES_DB=deepface \
  -p 5432:5432 \
  pgvector/pgvector:pg17
```

Or use `docker-compose.yml` in the project root (includes healthcheck).

### Docker Build

The image prebakes all model weights at build time so container startup is instant.

```bash
docker build -t deepface-server .
docker compose up
```

**Build-time requirements that are not obvious:**

| Requirement | Why |
|-------------|-----|
| `g++` (apt) | `insightface` compiles a C++ extension (`mesh_core_cython`) during `pip install` |
| `insightface>=0.7.3` | Buffalo_L delegates to InsightFace internally; not declared as a DeepFace dependency |
| `onnxruntime>=1.9.0` | Required by InsightFace at runtime |
| `albumentations` | Required by InsightFace |
| `tf-keras` | `retina-face` validates for this package at import time on TF 2.16+ |
| `tensorflow==2.19.0` | TF 2.18 has a packaging bug on aarch64: it caps `ml_dtypes<0.5.0` in metadata but its own code calls `ml_dtypes.float4_e2m1fn` which only exists in 0.5.0+ |

**For RTSP inside Docker:** the container cannot reach `localhost` on the host. Use `host.docker.internal` instead:
```
rtsp://host.docker.internal:8554/webcam_stream
```

### RTSP Source (MediaMTX + ffmpeg)

```bash
# MediaMTX — RTSP server
brew install mediamtx
mediamtx  # default config binds to :8554

# ffmpeg — push webcam to MediaMTX (macOS)
# MJPEG is recommended (intra-frame, no decoder artifacts when skipping frames)
ffmpeg -f avfoundation -framerate 30 -i "0" \
  -c:v mjpeg -q:v 3 \
  -f rtsp rtsp://localhost:8554/webcam_stream
```

### Running the Server

```bash
# Install dependencies in a venv
python3 -m venv deepface
deepface/bin/pip install -r requirements.txt

# Start
deepface/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On first start, DeepFace downloads Buffalo_L weights (~230 MB) to `~/.deepface/weights/`. Subsequent starts load from disk in under 10 seconds.

---

## Integration Patterns

### Register a face

```python
import httpx, base64

with open("alice.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

r = httpx.post("http://localhost:8000/register", json={
    "image": b64,
    "img_name": "alice"
})
print(r.json())  # {"inserted": 1, "img_name": "alice"}
```

### Search for a face

```python
with open("query.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

r = httpx.post("http://localhost:8000/search", json={"image": b64})
for face_result in r.json()["results"]:
    for match in face_result["matches"]:
        print(match["img_name"], match["distance"])
```

### Start an RTSP stream and receive webhooks

```python
# Start stream
r = httpx.post("http://localhost:8000/stream/start", json={
    "rtsp_url": "rtsp://localhost:8554/webcam_stream",
    "interval_seconds": 2.0,
    "webhook_url": "http://my-app/webhook/faces"
})
stream_id = r.json()["stream_id"]

# In your webhook handler:
# POST /webhook/faces receives:
# { stream_id, rtsp_url, timestamp, frames_processed, faces_found, matches: [...] }

# Stop stream
httpx.post(f"http://localhost:8000/stream/stop/{stream_id}")
```

### Multipart upload (for binary image data)

```python
with open("photo.jpg", "rb") as f:
    r = httpx.post("http://localhost:8000/register",
        files={"file": ("photo.jpg", f, "image/jpeg")},
        data={"img_name": "alice"}
    )
```

---

## Known Limitations and Gotchas

1. **Single worker only.** Do not set `WORKERS > 1`. DeepFace's model cache is process-local and not designed for concurrent access.

2. **normalization must be consistent.** Register and search must use the same `normalization` and `l2_normalize` values. The database does not store normalization type — mixing causes silent distance mismatches where correct matches score above threshold.

3. **RTSP buffer lag.** Without the `grab()`-flush approach, cv2 returns stale buffered frames. This has been fixed in `_read_latest_frame` but is worth understanding if you modify the stream loop.

4. **H264 decoder warnings.** When using H264-encoded RTSP, skipping frames via `grab()` breaks the P/B-frame reference chain, producing `decode_slice_header error` log spam from libavcodec. This is suppressed via `cv2.setLogLevel(0)` and does not affect correctness. Switch to MJPEG encoding to eliminate it entirely.

5. **`inserted: 0` is not an error.** DeepFace computes a hash of the face embedding before inserting. Re-registering the same image returns `inserted: 0` — the face is already in the database.

6. **Empty database 422.** `POST /build-index` and `POST /search` on an empty database raise `EmptyDatasource`. `/search` returns `{"results": []}` in this case; `/build-index` returns HTTP 422.

7. **Model warm-up on first start.** The lifespan handler preloads both the recognition model and detector at startup. The first request after a cold start has no additional latency. First-ever start downloads ~230 MB of weights.

8. **`confidence` from DeepFace is the detector probability, not recognition confidence.** The `confidence` column in `DeepFace.search()` results is how sure the face detector (mtcnn) was it found a face — it will be a flat value reflecting your camera setup. Recognition confidence is computed separately as `(1 - distance / threshold) * 100` and exposed as `recognition_confidence` in the webhook payload.

9. **TF 2.18 aarch64 packaging bug.** `tensorflow==2.18.0` declares `ml_dtypes<0.5.0` but uses `float4_e2m1fn` which only exists in 0.5.0+. This fails silently on x86 but crashes on aarch64 (Apple Silicon Docker). Use `tensorflow==2.19.0`.
