# Brainrot Video Generator - Architecture

## Overview
Full-stack app that converts text, documents, or voice input into TikTok-style "brainrot" videos — vertical (9:16) videos with gameplay footage backgrounds, Reddit-post styled captions, and AI narration.

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI |
| Frontend | React + TypeScript + Vite + Tailwind |
| Video | MoviePy + ffmpeg |
| TTS | edge-tts (Microsoft Edge TTS, free, no API key) |
| STT | openai-whisper (local, no API key) |
| LLM | Claude API (content summarization/rewriting) |
| Queue | Background tasks via asyncio (MVP), upgrade to Celery/Redis later |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  React Frontend                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │Text Input│ │File Upload│ │Voice Record/Upload│ │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘ │
│       └─────────────┼────────────────┘           │
│                     ▼                             │
│           POST /api/generate                      │
│                     │                             │
│           GET /api/jobs/{id} (poll)               │
│                     │                             │
│           GET /api/videos/{id} (download)         │
└─────────────────────┼─────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│                FastAPI Backend                    │
│                                                   │
│  ┌────────────────────────────────────────────┐  │
│  │            Video Generation Pipeline        │  │
│  │                                             │  │
│  │  1. Input Processing                        │  │
│  │     - Text: pass through                    │  │
│  │     - File: extract text (PDF/docx/txt)     │  │
│  │     - Audio: Whisper STT → text             │  │
│  │                                             │  │
│  │  2. Content Rewriting (optional)            │  │
│  │     - LLM rewrites into Reddit-post style   │  │
│  │     - Splits into sentences/segments        │  │
│  │                                             │  │
│  │  3. TTS Generation                          │  │
│  │     - edge-tts generates narration audio    │  │
│  │     - Word-level timestamps for captions    │  │
│  │                                             │  │
│  │  4. Video Compositing                       │  │
│  │     - Select random gameplay clip           │  │
│  │     - Overlay caption text (word highlight) │  │
│  │     - Mix in TTS audio                      │  │
│  │     - Output 1080x1920 MP4 (9:16)          │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  ┌─────────────┐  ┌──────────────────────────┐   │
│  │ Job Manager  │  │ Asset Manager            │   │
│  │ (in-memory)  │  │ (gameplay clips dir)     │   │
│  └─────────────┘  └──────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

## API Endpoints

### POST /api/generate
- **Input**: multipart/form-data with `text`, `file`, or `audio` field
- **Response**: `{ "job_id": "uuid", "status": "queued" }`

### GET /api/jobs/{job_id}
- **Response**: `{ "job_id": "uuid", "status": "queued|processing|complete|error", "progress": 0-100, "video_url": "/api/videos/{id}" }`

### GET /api/videos/{video_id}
- **Response**: MP4 file download

### GET /api/health
- **Response**: `{ "status": "ok" }`

## Project Structure

```
brainrot-generator/
├── backend/
│   ├── main.py                 # FastAPI app, routes
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── input_processor.py  # Text extraction, STT
│   │   ├── content_writer.py   # LLM rewriting (optional)
│   │   ├── tts_generator.py    # edge-tts narration + timestamps
│   │   └── video_composer.py   # MoviePy compositing
│   ├── models.py               # Pydantic models
│   ├── job_manager.py          # In-memory job tracking
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TextInput.tsx
│   │   │   ├── FileUpload.tsx
│   │   │   ├── JobProgress.tsx
│   │   │   └── VideoPlayer.tsx
│   │   └── api.ts              # API client
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── assets/
│   └── gameplay/               # Pre-recorded gameplay clips (user provides)
├── docker-compose.yml
└── README.md
```

## Key Design Decisions

1. **edge-tts over ElevenLabs/Coqui**: Free, no API key, high quality Microsoft voices, supports word-level timestamps via SSML
2. **MoviePy over raw ffmpeg**: Higher-level API, easier text overlays, good for compositing
3. **In-memory job queue (MVP)**: Simple asyncio background tasks, upgrade to Celery+Redis for scale
4. **Whisper local**: No API dependency for STT, runs on CPU (slower) or GPU
5. **Gameplay clips as assets**: User provides MP4 clips in assets/gameplay/. No copyright issues — user's own recordings.

## MVP Scope (This Session)
- [x] Architecture design
- [ ] Backend: FastAPI with /generate, /jobs, /videos endpoints
- [ ] Pipeline: text input → TTS → video compositing (text + gameplay)
- [ ] Frontend: basic React form, progress polling, video download
- [ ] Docker setup

## Future Enhancements
- Voice recording in browser (MediaRecorder API)
- Multiple video styles (split-screen, full-screen, picture-in-picture)
- Caption styling options (font, color, animation)
- Batch generation
- Video templates marketplace
- Redis + Celery for production job queue
