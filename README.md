# Brainrot Video Generator

[![Tests](https://github.com/andigenesis/brainrot-generator/actions/workflows/test.yml/badge.svg)](https://github.com/andigenesis/brainrot-generator/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org/)

**Turn any text into viral TikTok-style videos.** AI-powered brainrot video generator with word-by-word caption sync, gameplay backgrounds, and natural TTS narration — ready for TikTok, Reels, and Shorts.

## Overview

Brainrot Video Generator takes text, documents, or audio and produces vertical 9:16 MP4 videos with:

- **AI-powered narration** via Microsoft Edge TTS (JennyNeural voice) — free, no API key required
- **Word-by-word caption sync** — yellow highlight tracks each word as it's spoken, timed to real speech boundaries
- **Gameplay backgrounds** — Subway Surfers, Minecraft parkour, or your own clips
- **LLM script transformation** — rewrites dry text into unhinged Gen Z brainrot narration
- **Diagram overlays** — auto-generates visual diagrams for technical content
- **Full-stack web app** — React frontend with real-time job progress tracking

## Features

- **Text Input** — Paste any text and generate a video
- **File Upload** — Upload PDF, DOCX, or TXT files for automatic text extraction
- **Voice Input** — Upload audio for speech-to-text conversion
- **AI Narration** — Natural-sounding TTS via edge-tts with 4+ voice options
- **Script Transform** — LLM rewrites content into viral brainrot style (optional, toggleable)
- **Gameplay Backgrounds** — Subway Surfers, Minecraft parkour, or custom clips
- **Word-Level Captions** — Reddit-style captions with per-word yellow highlight synced to real speech timing
- **Diagram Overlays** — Auto-generated visual diagrams for technical explanations
- **9:16 Vertical Format** — Ready for TikTok, Instagram Reels, YouTube Shorts
- **Background Processing** — Submit jobs and poll progress via REST API
- **Real-Time Progress** — Frontend shows live progress bar with percentage updates

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- ffmpeg (`brew install ffmpeg` on macOS, `apt-get install ffmpeg` on Ubuntu)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173` and proxies API requests to the backend.

### Add Gameplay Clips

Place MP4 gameplay clips in `assets/gameplay/`:

```bash
mkdir -p assets/gameplay
# Add your own gameplay recordings (Subway Surfers, Minecraft, etc.)
cp ~/Videos/subway-surfers-clip.mp4 assets/gameplay/
```

The generator ships with 4 clips: 3 Subway Surfers and 1 Minecraft parkour. A random clip is selected for each video.

## Architecture

### Pipeline Workflow

```
                    ┌─────────────────────────────────────────────────┐
                    │              Brainrot Video Generator            │
                    └─────────────────────────────────────────────────┘

  ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  Input    │────>│   Script     │────>│     TTS      │────>│   Diagram    │
  │ Processor │     │ Transformer  │     │  Generator   │     │  Generator   │
  │           │     │  (Ollama)    │     │  (edge-tts)  │     │  (optional)  │
  └──────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                                       │                     │
       │  PDF/TXT/DOCX                         │  MP3 + word         │  PNG overlays
       │  → raw text                           │  timings            │  + timing data
       │                                       │                     │
       │           ┌───────────────────────────┘                     │
       │           │                                                 │
       │           ▼                                                 │
       │    ┌──────────────┐     ┌──────────────┐                    │
       │    │   Gameplay    │────>│    Video     │<───────────────────┘
       │    │   Selector    │     │  Composer    │
       │    │              │     │  (MoviePy)   │
       │    └──────────────┘     └──────────────┘
       │                                │
       │                                │  9:16 MP4 with:
       │                                │  - Gameplay background
       │                                │  - Word-synced captions
       │                                │  - Diagram overlays
       │                                ▼
       │                         ┌──────────────┐
       └────────────────────────>│   Job        │
                                 │   Manager    │
                                 └──────────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │   FastAPI     │
                                 │   REST API    │
                                 └──────────────┘
```

### Pipeline Stages

| Stage | Component | Description |
|-------|-----------|-------------|
| 1. Input | `input_processor.py` | Extracts text from PDF, DOCX, TXT files, or raw text |
| 2. Transform | `script_transformer.py` | LLM rewrites text into brainrot narration via Ollama (qwen3:8b) |
| 3. TTS | `tts_generator.py` | Generates MP3 audio + per-word timing via edge-tts WordBoundary events |
| 4. Diagrams | `diagram_generator.py` | Generates PNG diagram overlays with timing data (optional) |
| 5. Gameplay | `video_composer.py` | Selects random gameplay clip from `assets/gameplay/` |
| 6. Compose | `video_composer.py` | Composites 9:16 video with gameplay, captions, and diagrams via MoviePy |
| 7. Output | `job_manager.py` | Stores video, updates job status to COMPLETE |

### Caption Sync (Word-Level)

The caption system uses edge-tts `WordBoundary` events to achieve frame-accurate word highlighting:

1. **edge-tts** streams audio and emits `WordBoundary` events with offset/duration in 100-nanosecond ticks
2. **tts_generator** converts ticks to milliseconds and builds per-word timing arrays
3. **video_composer** renders each frame with PIL — the current word is highlighted in yellow, surrounding words in white
4. Caption blocks show ~6 words at a time in a Reddit-style overlay at the bottom third of the frame

### System Architecture

```
┌─────────────────────────────────────┐
│           React Frontend            │
│  TypeScript + Vite + Tailwind CSS   │
│  Components: TextInput, FileUpload, │
│  JobProgress, VideoPlayer           │
├─────────────────────────────────────┤
│           FastAPI Backend           │
│  REST API (4 endpoints)             │
│  Background task processing         │
│  Static file serving (production)   │
├─────────────────────────────────────┤
│         Processing Pipeline         │
│  input_processor → script_transform │
│  → tts_generator → diagram_gen     │
│  → video_composer                   │
├─────────────────────────────────────┤
│         External Services           │
│  edge-tts (Microsoft, free)         │
│  Ollama + qwen3:8b (local LLM)     │
│  ffmpeg (video encoding)            │
└─────────────────────────────────────┘
```

## API Reference

### `POST /api/generate` — Start Video Generation

Submit text or a file to start a new video generation job. Returns a job ID for polling.

**Request** (multipart form data):

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | One of `text` or `file` | — | Direct text input |
| `file` | file | One of `text` or `file` | — | PDF, DOCX, or TXT file upload |
| `transform` | boolean | No | `true` | Transform text into brainrot narration via LLM |
| `diagrams` | boolean | No | `true` | Generate diagram overlays for technical content |

**Response** (`200 OK`):

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "progress": 0
}
```

**Example** — Generate from text:

```bash
curl -X POST http://localhost:8000/api/generate \
  -F "text=The mitochondria is the powerhouse of the cell. It produces ATP through oxidative phosphorylation." \
  -F "transform=true" \
  -F "diagrams=false"
```

**Example** — Generate from file upload:

```bash
curl -X POST http://localhost:8000/api/generate \
  -F "file=@my-document.pdf" \
  -F "transform=true"
```

**Example** — Generate raw (no brainrot transform):

```bash
curl -X POST http://localhost:8000/api/generate \
  -F "text=Your exact narration script here." \
  -F "transform=false"
```

### `GET /api/jobs/{job_id}` — Check Job Status

Poll this endpoint to track video generation progress.

**Response** (`200 OK`):

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 60,
  "video_url": null,
  "error": null
}
```

When complete:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "progress": 100,
  "video_url": "/api/videos/550e8400-e29b-41d4-a716-446655440000",
  "error": null
}
```

**Job statuses**: `queued` → `processing` → `complete` | `error`

**Example**:

```bash
curl http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

### `GET /api/videos/{video_id}` — Download Video

Download the completed MP4 video file.

**Response**: `video/mp4` file download (`brainrot_{video_id}.mp4`)

**Example**:

```bash
curl -o brainrot_video.mp4 \
  http://localhost:8000/api/videos/550e8400-e29b-41d4-a716-446655440000
```

### `GET /api/health` — Health Check

**Response** (`200 OK`):

```json
{
  "status": "ok"
}
```

**Example**:

```bash
curl http://localhost:8000/api/health
```

### Full Workflow Example

```bash
# 1. Submit a generation job
JOB_ID=$(curl -s -X POST http://localhost:8000/api/generate \
  -F "text=Redis is actually insane. It stores everything in memory which makes it ridiculously fast." \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

echo "Job ID: $JOB_ID"

# 2. Poll until complete (check every 10 seconds)
while true; do
  STATUS=$(curl -s http://localhost:8000/api/jobs/$JOB_ID)
  echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{d[\"status\"]} - {d[\"progress\"]}%')"
  echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d['status'] in ('complete','error') else 1)" && break
  sleep 10
done

# 3. Download the video
curl -o brainrot_video.mp4 http://localhost:8000/api/videos/$JOB_ID
echo "Video saved to brainrot_video.mp4"
```

## Project Structure

```
brainrot-generator/
├── backend/
│   ├── main.py                          # FastAPI app with 4 API endpoints
│   ├── models.py                        # Pydantic models (JobStatus, requests, responses)
│   ├── job_manager.py                   # In-memory job tracking and state management
│   ├── pipeline/
│   │   ├── __init__.py                  # Pipeline exports
│   │   ├── input_processor.py           # PDF/DOCX/TXT text extraction
│   │   ├── script_transformer.py        # LLM brainrot narration (Ollama + qwen3:8b)
│   │   ├── tts_generator.py             # edge-tts with WordBoundary timing
│   │   ├── video_composer.py            # MoviePy 9:16 compositing with captions
│   │   └── diagram_generator.py         # Technical diagram overlay generation
│   ├── requirements.txt                 # Python dependencies
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api_error_handling.py   # API validation and error response tests
│   │   ├── test_edge_cases_comprehensive.py  # Edge case and boundary tests
│   │   ├── test_diagram_generator.py    # Diagram generation tests
│   │   └── test_script_transformer.py   # Script transformation tests
│   ├── test_imports.py                  # Import verification tests
│   └── test_synchronized_captions.py    # Word-level caption sync tests
├── frontend/
│   ├── src/
│   │   ├── App.tsx                      # Main app with generation workflow
│   │   ├── api.ts                       # API client (generate, pollJob, getVideoUrl)
│   │   ├── main.tsx                     # React entry point
│   │   ├── index.css                    # Tailwind CSS imports
│   │   └── components/
│   │       ├── TextInput.tsx            # Text input with character count
│   │       ├── FileUpload.tsx           # Drag-and-drop file upload
│   │       ├── JobProgress.tsx          # Real-time progress bar
│   │       └── VideoPlayer.tsx          # Video playback and download
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── tsconfig.node.json
├── assets/
│   └── gameplay/                        # Gameplay background clips (MP4)
│       ├── subway_surfers_01.mp4
│       ├── subway_surfers_02.mp4
│       ├── subway_surfers_03.mp4
│       └── minecraft_parkour_01.mp4
├── Dockerfile                           # Production Docker image
├── docker-compose.yml                   # Multi-service dev setup
├── railway.toml                         # Railway deployment config
├── .github/workflows/test.yml           # CI test pipeline
├── ARCHITECTURE.md                      # Detailed architecture docs
└── README.md
```

## Testing

### Running Tests

```bash
# Run all tests (113 pass, 10 skip)
python3 -m pytest backend/tests/ backend/test_imports.py backend/test_synchronized_captions.py -q

# Run specific test suites
python3 -m pytest backend/tests/test_api_error_handling.py -q       # API error handling
python3 -m pytest backend/tests/test_edge_cases_comprehensive.py -q  # Edge cases
python3 -m pytest backend/tests/test_diagram_generator.py -q         # Diagram generation
python3 -m pytest backend/tests/test_script_transformer.py -q        # Script transformation
python3 -m pytest backend/test_synchronized_captions.py -q           # Caption sync
python3 -m pytest backend/test_imports.py -q                         # Import checks

# Run with verbose output
python3 -m pytest backend/tests/ backend/test_imports.py backend/test_synchronized_captions.py -v

# Run with coverage
python3 -m pytest backend/tests/ --cov=backend --cov-report=term-missing
```

### Test Coverage

| Test Suite | Tests | Focus |
|------------|-------|-------|
| `test_api_error_handling.py` | API validation | Missing inputs, invalid files, 404s, error responses |
| `test_edge_cases_comprehensive.py` | Boundary cases | Empty text, huge inputs, unicode, concurrent jobs |
| `test_diagram_generator.py` | Diagram pipeline | Overlay generation, timing, image output |
| `test_script_transformer.py` | LLM transform | Brainrot narration, prompt structure, fallback |
| `test_synchronized_captions.py` | Caption sync | Word timing, highlight rendering, edge-tts integration |
| `test_imports.py` | Dependencies | All modules importable, no circular deps |

### CI/CD

Tests run automatically on push and PR to `main` via GitHub Actions:

```yaml
# .github/workflows/test.yml
- Python 3.12
- pip install -r backend/requirements.txt + pytest + pytest-asyncio
- pytest backend/tests/ -q --tb=short
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `backend/output/` | Directory for generated video files |
| `TEMP_DIR` | `backend/temp/` | Directory for temporary audio and image files |
| `GAMEPLAY_DIR` | `assets/gameplay/` | Directory containing gameplay MP4 clips |
| `STATIC_DIR` | `frontend/dist/` | Pre-built frontend static files (production) |
| `PORT` | `8000` | Server port (used in Docker/Railway) |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering (Docker) |
| `PYTHONDONTWRITEBYTECODE` | `1` | Skip .pyc file generation (Docker) |

The script transformer connects to a local Ollama instance for LLM-powered narration rewriting:

| Variable | Default | Description |
|----------|---------|-------------|
| Ollama URL | `http://localhost:11434/api/generate` | Ollama API endpoint (hardcoded) |
| Ollama Model | `qwen3:8b` | Model for brainrot narration transform |

## Docker Deployment

### Single Container (Production)

The Dockerfile builds a single container with the backend serving the pre-built frontend:

```bash
# Build frontend first
cd frontend && npm install && npm run build && cd ..

# Build Docker image
docker build -t brainrot-generator .

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/assets/gameplay:/app/assets/gameplay \
  -v $(pwd)/output:/app/output \
  brainrot-generator
```

Access the app at `http://localhost:8000`.

### Docker Compose (Development)

```bash
docker-compose up -d
```

This starts separate frontend and backend services:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

### Railway Deployment

The project includes `railway.toml` for one-click Railway deployment:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/api/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

Deploy to Railway:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway up
```

### Docker Image Details

- **Base**: `python:3.11-slim`
- **System deps**: ffmpeg, libsm6, libxext6 (for MoviePy/Pillow)
- **Non-root user**: `appuser` (UID 1000) for security
- **Health check**: Polls `/api/health` every 30s
- **Ports**: 8000 (configurable via `$PORT`)

## Development

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start dev server with auto-reload
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install

# Start dev server (proxies API to :8000)
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

### Code Quality

```bash
# Python — format and lint
pip install black ruff mypy
black backend/
ruff check backend/
mypy backend/

# TypeScript — lint
cd frontend
npm run lint
```

### Local LLM Setup (Script Transform)

The script transformer uses Ollama for brainrot narration. If Ollama is not running, the raw text is used as-is.

```bash
# Install Ollama (macOS)
brew install ollama

# Pull the model
ollama pull qwen3:8b

# Start Ollama server
ollama serve
```

### Adding Gameplay Clips

Drop MP4 files into `assets/gameplay/`. The generator randomly selects one per video.

Requirements for clips:
- Format: MP4 (H.264 recommended)
- Duration: At least 30 seconds (longer clips are trimmed to match audio length)
- Resolution: Any (automatically cropped to 9:16)
- Content: Satisfying, repetitive gameplay works best (Subway Surfers, Minecraft parkour, slicing games)

### Available TTS Voices

The edge-tts voice can be changed in `tts_generator.py`:

| Voice | Gender | Style |
|-------|--------|-------|
| `en-US-JennyNeural` (default) | Female | Friendly, conversational |
| `en-US-ChristopherNeural` | Male | Good for narration |
| `en-US-GuyNeural` | Male | Casual |
| `en-US-AriaNeural` | Female | News-style |

List all available voices:

```bash
python3 -c "import asyncio; import edge_tts; asyncio.run(edge_tts.list_voices())" | python3 -c "
import sys, json
voices = json.loads(sys.stdin.read())
for v in voices:
    if v['Locale'].startswith('en'):
        print(f\"{v['ShortName']:40s} {v['Gender']:10s} {v['Locale']}\")
"
```

## Tech Stack

**Backend (Python)**:
- **Web Framework**: FastAPI 0.109
- **TTS Engine**: edge-tts 7.2.7 (Microsoft Edge, free, no API key)
- **TTS Fallback**: gTTS 2.5 (Google, no word timing)
- **Video Compositing**: MoviePy 1.0.3 + ffmpeg
- **Image Processing**: Pillow 10.2
- **PDF Parsing**: PyPDF2 3.0
- **HTTP Client**: httpx 0.27 (for Ollama API)
- **Async Files**: aiofiles 23.2
- **Data Validation**: Pydantic 2.5
- **ASGI Server**: Uvicorn 0.27

**Frontend (TypeScript)**:
- **UI Framework**: React 18.2
- **Build Tool**: Vite 5.0
- **Styling**: Tailwind CSS 3.4
- **Form Components**: @tailwindcss/forms
- **Type Checking**: TypeScript 5.2
- **Linting**: ESLint with React hooks plugin

**Infrastructure**:
- **Video Encoding**: ffmpeg (system dependency)
- **Local LLM**: Ollama + qwen3:8b (for script transformation)
- **CI/CD**: GitHub Actions
- **Deployment**: Docker, Railway

## Performance Notes

- **Video encoding is the bottleneck**: ~16 minutes for a 2.5-minute video. MoviePy renders frame-by-frame at ~5 fps due to per-frame caption compositing
- **TTS generation** is fast: ~5 seconds for 500 words via edge-tts
- **Script transformation** via Ollama depends on local hardware: ~10-30 seconds on Apple Silicon
- **Total pipeline time**: 5-20 minutes depending on text length and hardware

## Roadmap

- [ ] GPU-accelerated encoding (NVENC/VideoToolbox) for 10x faster video rendering
- [ ] Batch generation — queue multiple videos from a document
- [ ] Voice cloning — custom voice via input audio sample
- [ ] Multiple caption styles — Reddit, subtitle, karaoke, bouncing text
- [ ] Background music — auto-mix royalty-free tracks with volume ducking
- [ ] Webhook notifications — callback URL when job completes
- [ ] S3/GCS storage — upload completed videos to cloud storage
- [ ] Additional gameplay sources — auto-download clips from configured sources
- [ ] Streaming progress via SSE — replace polling with server-sent events
- [ ] Mobile-optimized frontend — PWA with share-to-TikTok integration

## License

MIT License
