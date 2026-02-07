# Brainrot Video Generator

Convert text, documents, or voice into TikTok-style "brainrot" videos with gameplay backgrounds, Reddit-styled captions, and AI narration.

## Features

- **Text Input**: Paste any text and generate a video
- **File Upload**: Upload PDF, DOCX, or TXT files
- **Voice Input**: Upload audio for speech-to-text conversion
- **AI Narration**: Natural-sounding TTS via edge-tts
- **Gameplay Backgrounds**: Subway Surfers, Minecraft parkour style
- **Reddit-Style Captions**: Word-by-word highlighting synced to narration
- **9:16 Vertical Format**: Ready for TikTok, Reels, Shorts

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- ffmpeg installed (`brew install ffmpeg` on macOS)

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Add Gameplay Clips
Place MP4 gameplay clips in `assets/gameplay/`:
```bash
mkdir -p assets/gameplay
# Add your own gameplay recordings (Subway Surfers, Minecraft, etc.)
cp ~/Videos/subway-surfers-clip.mp4 assets/gameplay/
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate` | POST | Submit text/file for video generation |
| `/api/jobs/{id}` | GET | Check job status and progress |
| `/api/videos/{id}` | GET | Download generated video |
| `/api/health` | GET | Health check |

## Tech Stack

- **Backend**: FastAPI + MoviePy + edge-tts
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Video**: MoviePy + ffmpeg
- **TTS**: edge-tts (Microsoft, free, no API key)

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full design.
