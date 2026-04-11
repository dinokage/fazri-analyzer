# DeepFace Integration Reference

> **Purpose:** Drop this file into any Claude Code session to get complete, accurate context for integrating DeepFace into a project. All signatures, return shapes, defaults, and constraints are sourced directly from the codebase (v0.0.99).

---

## 1. What DeepFace Is

A Python library (MIT license) for face recognition and facial attribute analysis. It wraps multiple pre-trained deep learning models behind a single unified API. The core pipeline is: **Detect → Align → Normalize → Represent → Verify**.

**Install:**
```bash
pip install deepface
# or from source:
pip install -e /path/to/deepface
```

**Core dependencies:** `tensorflow`, `keras`, `opencv-python`, `numpy`, `pandas`, `Pillow`, `mtcnn`, `retina-face`, `Flask`, `flask_cors`, `gdown`, `fire`, `lightphe`, `lightdsa`, `python-dotenv`

**Critical import note:** DeepFace sets `os.environ["TF_USE_LEGACY_KERAS"] = "1"` before importing TF. If your project also imports TF, import DeepFace first or set this env var yourself.

```python
from deepface import DeepFace
```

---

## 2. Input Types (Accepted Everywhere)

All image-accepting functions accept any of:
- `str` — file path or base64-encoded image string
- `np.ndarray` — BGR format (OpenCV convention, NOT RGB)
- `IO[bytes]` — file object opened in binary mode (must support `.read`)
- `List[float]` — pre-computed embedding vector (only for `verify`)
- HTTP URLs are also accepted as strings

---

## 3. Public API — All Functions

### 3.1 `verify` — Compare two faces

```python
result = DeepFace.verify(
    img1_path,                        # str | ndarray | IO[bytes] | List[float]
    img2_path,                        # str | ndarray | IO[bytes] | List[float]
    model_name="VGG-Face",            # see §5 for options
    detector_backend="opencv",        # see §6 for options
    distance_metric="cosine",         # "cosine" | "euclidean" | "euclidean_l2" | "angular"
    enforce_detection=True,           # raise FaceNotDetected if no face found
    align=True,
    expand_percentage=0,              # expand detected face area by % (int)
    normalization="base",             # see §7 for options
    silent=False,
    threshold=None,                   # float override; None = use pre-tuned default
    anti_spoofing=False,              # requires FasNet model
)
```

**Returns `dict`:**
```python
{
    "verified": bool,           # True = same person
    "distance": float,          # lower = more similar
    "threshold": float,         # the threshold used
    "confidence": float,        # 0–100 scale
    "model": str,
    "distance_metric": str,
    "facial_areas": {
        "img1": {"x": int, "y": int, "w": int, "h": int},
        "img2": {"x": int, "y": int, "w": int, "h": int},
    },
    "time": float,              # seconds
}
```

---

### 3.2 `analyze` — Facial attribute detection

```python
results = DeepFace.analyze(
    img_path,                                           # str | ndarray | IO[bytes]
                                                        # OR list of any of the above (batch)
    actions=("emotion", "age", "gender", "race"),       # subset allowed
    enforce_detection=True,
    detector_backend="opencv",
    align=True,
    expand_percentage=0,
    silent=False,
    anti_spoofing=False,
)
```

**Returns `List[Dict]`** (one dict per detected face); `List[List[Dict]]` for batched input:
```python
[{
    "region": {"x": int, "y": int, "w": int, "h": int},
    "face_confidence": float,
    "age": float,
    "dominant_gender": "Man" | "Woman",
    "gender": {"Man": float, "Woman": float},
    "dominant_emotion": "sad"|"angry"|"surprise"|"fear"|"happy"|"disgust"|"neutral",
    "emotion": {"sad": float, "angry": float, "surprise": float,
                 "fear": float, "happy": float, "disgust": float, "neutral": float},
    "dominant_race": "indian"|"asian"|"latino hispanic"|"black"|"middle eastern"|"white",
    "race": {"indian": float, "asian": float, "latino hispanic": float,
              "black": float, "middle eastern": float, "white": float},
}]
```

---

### 3.3 `find` — Search a local image database (stateful)

Stores embeddings in a `.pkl` file alongside the database directory; refreshes on change.

```python
dfs = DeepFace.find(
    img_path,                   # str | ndarray | IO[bytes]
    db_path,                    # str — path to folder containing images
    model_name="VGG-Face",
    distance_metric="cosine",
    enforce_detection=True,
    detector_backend="opencv",
    align=True,
    similarity_search=False,    # True = lookalike search, False = identity match
    k=None,                     # int | None — top-k results; None = all within threshold
    expand_percentage=0,
    threshold=None,
    normalization="base",
    silent=False,
    refresh_database=True,      # re-sync pkl with db_path contents
    anti_spoofing=False,
    batched=False,              # True = faster for large DBs, returns List[Dict] not List[DataFrame]
    credentials=None,           # LightDSA instance or dict for pickle signing
)
```

**Returns `List[pd.DataFrame]`** (one DataFrame per detected face in `img_path`).
When `batched=True`, returns `List[List[Dict]]` with same keys as DataFrame columns.

DataFrame columns:
- `identity` — matched image path
- `target_x`, `target_y`, `target_w`, `target_h` — bounding box in DB image
- `source_x`, `source_y`, `source_w`, `source_h` — bounding box in query image
- `threshold`, `distance`, `confidence`

---

### 3.4 `represent` — Generate embedding vectors

```python
embeddings = DeepFace.represent(
    img_path,                   # str | ndarray | IO[bytes]
                                # OR Sequence of any of the above (batch)
    model_name="VGG-Face",
    enforce_detection=True,
    detector_backend="opencv",
    align=True,
    expand_percentage=0,
    normalization="base",
    anti_spoofing=False,
    max_faces=None,             # int | None — limit faces processed
    l2_normalize=False,         # unit-vector normalize output
    minmax_normalize=False,     # scale output to [0, 1]
    return_face=False,          # include face crop in result
    cryptosystem=None,          # LightPHE instance for homomorphic encryption
)
```

**Returns `List[Dict]`**; `List[List[Dict]]` for batch input:
```python
[{
    "embedding": List[float],       # dims depend on model (see §5)
    "facial_area": {"x": int, "y": int, "w": int, "h": int},
    "face_confidence": float,
    # if return_face=True:
    "face": np.ndarray,             # RGB, normalized [0,1] float32
    # if cryptosystem provided:
    "encrypted_embedding": List[Any],
}]
```

---

### 3.5 `extract_faces` — Detect and crop faces

```python
faces = DeepFace.extract_faces(
    img_path,                   # str | ndarray | IO[bytes]
                                # OR list of any of the above (batch)
    detector_backend="opencv",
    enforce_detection=True,
    align=True,
    expand_percentage=0,
    grayscale=False,            # DEPRECATED — use color_face="gray" instead
    color_face="rgb",           # "rgb" | "bgr" | "gray"
    normalize_face=True,        # divide pixel values by 255
    anti_spoofing=False,
)
```

**Returns `List[Dict]`**; `List[List[Dict]]` for batch input:
```python
[{
    "face": np.ndarray,         # shape (H, W, C), dtype float32, values in [0,1] if normalized
    "facial_area": {
        "x": int, "y": int, "w": int, "h": int,
        "left_eye": (int, int),   # coordinates relative to person (not observer)
        "right_eye": (int, int),
    },
    "confidence": float,
    # if anti_spoofing=True:
    "is_real": bool,
    "antispoof_score": float,
}]
```

---

### 3.6 `stream` — Real-time video analysis

```python
DeepFace.stream(
    db_path="",                 # str — face database folder (empty = no recognition)
    model_name="VGG-Face",
    detector_backend="opencv",
    distance_metric="cosine",
    enable_face_analysis=True,  # show age/gender/emotion/race overlays
    source=0,                   # int (camera index) or str (video file path)
    time_threshold=5,           # seconds between recognition attempts (min 1)
    frame_threshold=5,          # frames between recognition attempts (min 1)
    anti_spoofing=False,
    output_path=None,           # str | None — save annotated video to path
    debug=False,                # save per-frame outcomes
)
# Returns None. Blocking call. Press Q to exit.
```

---

### 3.7 `register` — Register face to vector database

```python
result = DeepFace.register(
    img,                        # str | ndarray | IO[bytes] | list of any
    img_name=None,              # str | None — name stored in DB; extracted from path if None
    model_name="VGG-Face",
    detector_backend="opencv",
    enforce_detection=True,
    align=True,
    l2_normalize=False,
    expand_percentage=0,
    normalization="base",
    anti_spoofing=False,
    database_type="postgres",   # see §8 for options
    connection_details=None,    # dict | str | None
    connection=None,            # existing DB connection object
)
# Returns: {"inserted": int}
```

---

### 3.8 `search` — Search vector database (stateless)

```python
dfs = DeepFace.search(
    img,                        # str | ndarray | IO[bytes] | list of any
    model_name="VGG-Face",
    detector_backend="opencv",
    distance_metric="cosine",
    enforce_detection=True,
    align=True,
    l2_normalize=False,
    expand_percentage=0,
    normalization="base",
    anti_spoofing=False,
    similarity_search=False,
    k=None,
    database_type="postgres",
    connection_details=None,
    connection=None,
    search_method="exact",      # "exact" | "ann" (ann requires build_index first)
)
# Returns List[pd.DataFrame]
```

DataFrame columns: `id`, `img_name`, `model_name`, `aligned`, `l2_normalized`, `search_method`, `confidence`, `target_x/y/w/h`, `threshold`, `distance_metric`, `distance`

---

### 3.9 `build_index` — Build ANN index for fast search

```python
DeepFace.build_index(
    model_name="VGG-Face",
    detector_backend="opencv",
    align=True,
    l2_normalize=False,
    database_type="postgres",
    connection=None,
    connection_details=None,
    max_neighbors_per_node=32,
)
# Returns None. Run once after registering all faces, before using search_method="ann".
```

---

### 3.10 `build_model` — Preload a model into cache

```python
model = DeepFace.build_model(
    model_name,                 # see §5, §6 for names
    task="facial_recognition",  # "facial_recognition" | "facial_attribute"
                                # | "face_detector" | "spoofing"
)
# Returns the model object. Subsequent calls return the cached singleton.
```

Useful to call on app startup to avoid first-request latency.

---

## 4. Exceptions

All in `deepface.modules.exceptions`. All inherit from `ValueError`.

```python
from deepface.modules.exceptions import (
    FaceNotDetected,        # no face found in image
    ImgNotFound,            # file path invalid or image unreadable
    PathNotFound,           # directory path does not exist
    SpoofDetected,          # anti_spoofing=True and face is fake
    EmptyDatasource,        # database/directory is empty
    DimensionMismatchError, # embedding size mismatch
    InvalidEmbeddingsShapeError,
    DataTypeError,
    UnimplementedError,
    DuplicateEntryError,    # duplicate face in vector DB
)
```

**Typical error handling pattern:**
```python
from deepface import DeepFace
from deepface.modules.exceptions import FaceNotDetected, SpoofDetected

try:
    result = DeepFace.verify("img1.jpg", "img2.jpg", anti_spoofing=True)
except FaceNotDetected:
    # handle missing face — or retry with enforce_detection=False
except SpoofDetected:
    # handle liveness failure
except ValueError as e:
    # catch-all for all deepface errors
```

---

## 5. Face Recognition Models

| `model_name` | Embedding dims | Notes |
|---|---|---|
| `"VGG-Face"` | 4096 | **Default.** Best general accuracy. |
| `"Facenet"` | 128 | Fast, lightweight |
| `"Facenet512"` | 512 | Higher accuracy variant |
| `"ArcFace"` | 512 | Strong for verification |
| `"SFace"` | 128 | Lightweight, mobile-friendly |
| `"GhostFaceNet"` | 512 | Efficient, high accuracy |
| `"Buffalo_L"` | 512 | InsightFace model |
| `"OpenFace"` | 128 | Older, lighter |
| `"DeepFace"` | 4096 | Facebook research model |
| `"DeepID"` | 160 | Older model |
| `"Dlib"` | 128 | Requires `dlib` package |

**Pre-tuned cosine thresholds** (lower distance = same person):

| Model | cosine | euclidean | euclidean_l2 | angular |
|---|---|---|---|---|
| VGG-Face | 0.68 | 1.17 | 1.17 | 0.39 |
| Facenet | 0.40 | 10.0 | 0.80 | 0.33 |
| Facenet512 | 0.30 | 23.56 | 1.04 | 0.35 |
| ArcFace | 0.68 | 4.15 | 1.13 | 0.39 |
| SFace | 0.593 | 10.734 | 1.055 | 0.36 |
| GhostFaceNet | 0.65 | 35.71 | 1.10 | 0.38 |
| Buffalo_L | 0.55 | 0.6 | 1.1 | 0.45 |
| Dlib | 0.07 | 0.6 | 0.4 | 0.12 |
| OpenFace | 0.10 | 0.55 | 0.55 | 0.11 |
| DeepFace | 0.23 | 64.0 | 0.64 | 0.12 |
| DeepID | 0.015 | 45.0 | 0.17 | 0.04 |

---

## 6. Face Detector Backends

| `detector_backend` | Notes |
|---|---|
| `"opencv"` | **Default.** Fast, CPU-only, lower accuracy |
| `"retinaface"` | High accuracy, recommended for production |
| `"mtcnn"` | Good accuracy, multi-face support |
| `"ssd"` | Fast, single shot |
| `"dlib"` | Requires `dlib` package |
| `"mediapipe"` | Very fast, good for real-time |
| `"yolov8n"` / `"yolov8m"` / `"yolov8l"` | YOLO v8 variants |
| `"yolov11n"` / `"yolov11s"` / `"yolov11m"` / `"yolov11l"` | YOLO v11 variants |
| `"yolov12n"` / `"yolov12s"` / `"yolov12m"` / `"yolov12l"` | YOLO v12 variants |
| `"yunet"` | Lightweight |
| `"fastmtcnn"` | Faster MTCNN variant |
| `"centerface"` | Good accuracy |
| `"skip"` | **Bypass detection** — treats entire image as face |

Use `"skip"` when you've already cropped the face and want to skip detection entirely.

---

## 7. Normalization Options

`normalization` parameter in `verify`, `find`, `represent`, `register`, `search`:

| Value | Description |
|---|---|
| `"base"` | **Default.** Scales to [0, 255] range |
| `"raw"` | No normalization |
| `"Facenet"` | Facenet-specific (mean/std) |
| `"Facenet2018"` | Scale to [-1, 1] |
| `"VGGFace"` | VGGFace-specific mean subtraction |
| `"VGGFace2"` | VGGFace2-specific |
| `"ArcFace"` | ArcFace-specific normalization |

**Rule:** Match normalization to your chosen model for best results (e.g., use `"ArcFace"` with `model_name="ArcFace"`).

---

## 8. Vector Database Integration

For `register`, `search`, `build_index`:

### Supported `database_type` values

| Value | Env var for connection | Notes |
|---|---|---|
| `"postgres"` | `DEEPFACE_POSTGRES_URI` | Requires pgvector extension |
| `"pgvector"` | `DEEPFACE_POSTGRES_URI` | Explicit pgvector |
| `"mongo"` | `DEEPFACE_MONGO_URI` | MongoDB Atlas or local |
| `"neo4j"` | `DEEPFACE_NEO4J_URI` | Graph DB |
| `"weaviate"` | `DEEPFACE_WEAVIATE_URI` | Vector-native DB |
| `"pinecone"` | `DEEPFACE_PINECONE_API_KEY` | Managed vector DB |

**Alternative:** Pass `DEEPFACE_CONNECTION_DETAILS` env var (overrides all DB-specific URIs).

### Connection via env var (preferred):
```bash
export DEEPFACE_DATABASE_TYPE=postgres
export DEEPFACE_POSTGRES_URI=postgresql://user:pass@host:5432/dbname
```

### Connection via code:
```python
DeepFace.register(img, database_type="postgres", connection_details="postgresql://...")
# OR pass an existing connection object:
import psycopg2
conn = psycopg2.connect(...)
DeepFace.register(img, database_type="postgres", connection=conn)
```

### ANN search workflow:
```python
# 1. Register all faces
DeepFace.register("face.jpg", database_type="postgres")

# 2. Build index once
DeepFace.build_index(model_name="VGG-Face", database_type="postgres")

# 3. Search with ANN
results = DeepFace.search("query.jpg", database_type="postgres", search_method="ann")
```

---

## 9. REST API

### Start the server

```bash
# Development
python -c "from deepface.api.src.app import create_app; create_app().run(port=5000)"

# Production (gunicorn)
gunicorn --workers 4 --bind 0.0.0.0:5000 "deepface.api.src.app:create_app()"
```

### Environment variables

| Variable | Purpose |
|---|---|
| `DEEPFACE_DATABASE_TYPE` | DB backend (default: `"postgres"`) |
| `DEEPFACE_CONNECTION_DETAILS` | DB connection string |
| `DEEPFACE_POSTGRES_URI` | PostgreSQL URI |
| `DEEPFACE_FACE_RECOGNITION_MODELS` | Comma-separated models to preload on startup |
| `DEEPFACE_FACE_DETECTION_MODELS` | Comma-separated detectors to preload on startup |
| `DEEPFACE_AUTH_TOKEN` | Bearer token for API authentication |

### Endpoints

All endpoints accept **multipart/form-data** (file upload) or **JSON** or **form-data** (base64/path).

#### `GET /`
Health check. Returns welcome string.

#### `POST /represent`
```json
// Request (JSON)
{
  "img": "<base64 or path>",
  "model_name": "VGG-Face",
  "detector_backend": "opencv",
  "enforce_detection": true,
  "align": true,
  "anti_spoofing": false,
  "max_faces": null
}
// Request (multipart): field name = "img"
```

#### `POST /verify`
```json
// Request
{
  "img1": "<base64 or path>",
  "img2": "<base64 or path>",
  "model_name": "VGG-Face",
  "detector_backend": "opencv",
  "distance_metric": "cosine",
  "align": true,
  "enforce_detection": true,
  "anti_spoofing": false
}
// multipart: field names = "img1", "img2"
```

#### `POST /analyze`
```json
{
  "img": "<base64 or path>",
  "actions": ["age", "gender", "emotion", "race"],
  "detector_backend": "opencv",
  "enforce_detection": true,
  "align": true,
  "anti_spoofing": false
}
```

#### `POST /register` (requires DB env vars)
```json
{
  "img": "<base64 or path>",
  "img_name": "person_001",
  "model_name": "VGG-Face",
  "detector_backend": "opencv",
  "enforce_detection": true,
  "align": true,
  "l2_normalize": false,
  "expand_percentage": 0,
  "normalization": "base",
  "anti_spoofing": false
}
```

#### `POST /search` (requires DB env vars)
```json
{
  "img": "<base64 or path>",
  "model_name": "VGG-Face",
  "detector_backend": "opencv",
  "distance_metric": "cosine",
  "enforce_detection": true,
  "align": true,
  "l2_normalize": false,
  "search_method": "exact",
  "similarity_search": false,
  "k": null
}
```

#### `POST /build/index` (requires DB env vars)
```json
{
  "model_name": "VGG-Face",
  "detector_backend": "opencv",
  "align": true,
  "l2_normalize": false
}
```

### Authentication
If `DEEPFACE_AUTH_TOKEN` is set, all requests require:
```
Authorization: Bearer <token>
```
Requests without a valid token return `401`.

---

## 10. Common Integration Patterns

### Pattern A: Simple face verification (two images)
```python
from deepface import DeepFace
from deepface.modules.exceptions import FaceNotDetected

def are_same_person(img1, img2, strict=True):
    try:
        result = DeepFace.verify(
            img1, img2,
            model_name="ArcFace",
            detector_backend="retinaface",
            distance_metric="cosine",
            enforce_detection=strict,
        )
        return result["verified"], result["confidence"]
    except FaceNotDetected:
        return False, 0.0
```

### Pattern B: Preload models at app startup
```python
# Run once at startup — avoids cold start on first request
DeepFace.build_model("ArcFace", task="facial_recognition")
DeepFace.build_model("retinaface", task="face_detector")
```

### Pattern C: Local file-based database search
```python
# Directory structure:
# faces_db/
#   alice/photo1.jpg
#   bob/photo2.jpg

results = DeepFace.find(
    "query.jpg",
    db_path="./faces_db",
    model_name="ArcFace",
    detector_backend="retinaface",
)
for df in results:  # one df per face found in query image
    if not df.empty:
        top_match = df.iloc[0]
        print(top_match["identity"], top_match["distance"])
```

### Pattern D: Extract and store embeddings for later comparison
```python
# Extract once, store the List[float]
reps = DeepFace.represent("face.jpg", model_name="ArcFace", l2_normalize=True)
embedding = reps[0]["embedding"]  # List[float], 512-dim for ArcFace

# Later: verify against stored embedding (skip re-detection)
result = DeepFace.verify(
    embedding,          # pre-computed
    "new_face.jpg",     # live image
    model_name="ArcFace",
)
```

### Pattern E: Batch processing images
```python
import os

image_paths = [os.path.join("faces", f) for f in os.listdir("faces")]

# Process as batch
all_embeddings = DeepFace.represent(image_paths, model_name="ArcFace")
# all_embeddings is List[List[Dict]] when input is a sequence
```

### Pattern F: Anti-spoofing + verification
```python
result = DeepFace.verify(
    "selfie.jpg", "id_card.jpg",
    anti_spoofing=True,         # raises SpoofDetected if fake
    model_name="ArcFace",
    detector_backend="retinaface",
)
```

### Pattern G: Demographic analysis (selective attributes)
```python
# Only compute what you need — skip unused models
result = DeepFace.analyze(
    "face.jpg",
    actions=["age", "gender"],  # skip emotion/race for speed
    detector_backend="retinaface",
    enforce_detection=False,    # don't crash on low-res images
)
face = result[0]
print(face["age"], face["dominant_gender"])
```

### Pattern H: Flask/FastAPI endpoint wrapping DeepFace
```python
from flask import Flask, request, jsonify
from deepface import DeepFace
from deepface.modules.exceptions import FaceNotDetected, SpoofDetected
import base64, numpy as np

app = Flask(__name__)

# Preload on startup
with app.app_context():
    DeepFace.build_model("ArcFace", task="facial_recognition")
    DeepFace.build_model("retinaface", task="face_detector")

@app.post("/verify")
def verify():
    data = request.get_json()
    try:
        result = DeepFace.verify(
            data["img1"], data["img2"],
            model_name="ArcFace",
            detector_backend="retinaface",
        )
        return jsonify(result)
    except FaceNotDetected as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

## 11. Performance & Configuration Guidance

### Model selection tradeoffs

| Goal | Recommended |
|---|---|
| Highest accuracy | `Facenet512` + `retinaface` |
| Balanced speed/accuracy | `ArcFace` + `retinaface` |
| Fastest CPU | `SFace` + `opencv` |
| Real-time video | `SFace` + `mediapipe` |
| General default | `VGG-Face` + `opencv` (library default) |

### Detector tradeoffs

| Goal | Recommended |
|---|---|
| Best accuracy | `retinaface` |
| Fastest | `opencv` or `mediapipe` |
| Multi-face scenes | `mtcnn` or `retinaface` |
| Skip detection (pre-cropped) | `skip` |

### Memory & cold start

- Models are singletons — call `build_model()` at startup to pay load cost once.
- VGG-Face: ~500MB RAM. Facenet/ArcFace: ~100–200MB. SFace: ~5MB.
- TF logs suppressed by default via `TF_CPP_MIN_LOG_LEVEL=3`.

### `enforce_detection=False`

Use when:
- Processing low-resolution images
- Images may not contain a face (don't want exceptions)
- You've pre-cropped faces and are using `detector_backend="skip"`

### `expand_percentage`

Expands the detected bounding box by N% before passing to recognition model. Useful when faces are tightly cropped. Values 10–20 help in edge cases.

---

## 12. Docker / Deployment

### Dockerfile summary
- Base: `python:3.8.12`
- System deps: `ffmpeg libsm6 libxext6 libhdf5-dev`
- Exposes: `5000`
- Server: `gunicorn`

### Docker Compose (API + PostgreSQL + pgvector)
```bash
docker-compose up
# API at http://localhost:5000
# Postgres at localhost:5432
```

### Minimal docker-compose for API-only
```yaml
services:
  deepface:
    build: .
    ports: ["5000:5000"]
    environment:
      - DEEPFACE_DATABASE_TYPE=postgres
      - DEEPFACE_POSTGRES_URI=postgresql://...
      - DEEPFACE_AUTH_TOKEN=secret
      - DEEPFACE_FACE_RECOGNITION_MODELS=ArcFace
      - DEEPFACE_FACE_DETECTION_MODELS=retinaface
```

---

## 13. File Structure (Key Paths)

```
deepface/
├── DeepFace.py                          # ALL public API — start here
├── modules/
│   ├── verification.py                  # verify() implementation + distance metrics
│   ├── recognition.py                   # find() implementation
│   ├── representation.py                # represent() implementation
│   ├── demography.py                    # analyze() implementation
│   ├── detection.py                     # extract_faces() implementation
│   ├── streaming.py                     # stream() implementation
│   ├── modeling.py                      # singleton model cache
│   ├── datastore.py                     # register/search/build_index
│   ├── preprocessing.py                 # alignment + normalization
│   └── exceptions.py                    # all custom exceptions
├── models/
│   ├── FacialRecognition.py             # abstract base class
│   ├── Detector.py                      # abstract base + FacialAreaRegion dataclass
│   ├── Demography.py                    # abstract base
│   ├── facial_recognition/              # VGGFace.py, Facenet.py, ArcFace.py, ...
│   ├── face_detection/                  # OpenCv.py, RetinaFace.py, Mtcnn.py, ...
│   └── demography/                      # Age.py, Gender.py, Emotion.py, Race.py
├── config/
│   ├── threshold.py                     # per-model distance thresholds (dict)
│   ├── confidence.py                    # confidence score parameters
│   └── minmax.py                        # normalization bounds
├── commons/
│   ├── image_utils.py                   # load_image(), base64 handling, file I/O
│   ├── weight_utils.py                  # model weight download manager
│   └── logger.py                        # Logger class
└── api/
    └── src/
        ├── app.py                       # create_app() Flask factory
        ├── modules/core/routes.py       # all endpoint definitions
        ├── modules/core/service.py      # business logic for API
        └── dependencies/variables.py   # env var parsing
```

---

## 14. Known Gotchas

1. **BGR not RGB**: NumPy arrays must be in BGR (OpenCV default). If you have RGB, convert: `img_bgr = img_rgb[:, :, ::-1]`

2. **TF import order**: `os.environ["TF_USE_LEGACY_KERAS"] = "1"` must be set before TF imports. DeepFace does this automatically when imported first.

3. **`find()` pkl file**: Creates `ds_model_VGG-Face_detector_opencv_aligned_normalization_base_expand_0.pkl` in `db_path`. Delete it if you change model/detector settings or it will use stale embeddings. Set `refresh_database=True` (default) to auto-sync on file changes.

4. **`verify()` with pre-computed embeddings**: Both inputs can be `List[float]` (embeddings), but they must have been computed with the same model, normalization, and alignment settings.

5. **`analyze()` returns a list even for single face**: Always index `result[0]` for the first face.

6. **Batch input**: When passing a Python list as `img_path`, the return type changes from `List[Dict]` to `List[List[Dict]]` (one list per input image).

7. **Anti-spoofing requires PyTorch**: `FasNet` model depends on `torch`. Install separately: `pip install torch`.

8. **Dlib requires cmake + compilation**: `pip install dlib` needs `cmake` and a C++ compiler.

9. **Model weights auto-download**: First use of any model triggers a download from Google Drive via `gdown`. Ensure network access or pre-download weights to `~/.deepface/weights/`.

10. **Thread safety**: The singleton model cache is not thread-safe by default. In multi-threaded servers, call `build_model()` for all models before serving requests.
