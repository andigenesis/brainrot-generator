# Brainrot Video Generator - Backend

FastAPI backend for generating TikTok-style "brainrot" videos with gameplay backgrounds and AI narration.

## Features

- **Text-to-Speech**: Uses Microsoft Edge TTS (free, no API key required)
- **Video Compositing**: MoviePy for overlay text on gameplay footage
- **File Upload**: Supports PDF and TXT file text extraction
- **Background Processing**: Async job queue with progress tracking
- **RESTful API**: Clean API with job status polling

## Project Structure

```
backend/
├── main.py                 # FastAPI app and routes
├── models.py               # Pydantic models
├── job_manager.py          # In-memory job tracking
├── pipeline/
│   ├── __init__.py
│   ├── tts_generator.py    # Edge-TTS narration
│   ├── video_composer.py   # MoviePy compositing
│   └── input_processor.py  # PDF/TXT text extraction
├── requirements.txt
├── output/                 # Generated videos (auto-created)
└── temp/                   # Temporary audio files (auto-created)
```

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Add gameplay clips**:
   ```bash
   mkdir -p ../assets/gameplay
   # Copy your MP4 gameplay recordings to ../assets/gameplay/
   ```

3. **Install system dependencies** (for MoviePy):
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt install ffmpeg`

## Running the Server

```bash
# Development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Server will be available at `http://localhost:8000`

## API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints

#### POST /api/generate
Generate a new brainrot video.

**Request** (multipart/form-data):
- `text` (optional): Direct text input
- `file` (optional): PDF or TXT file upload

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "progress": 0
}
```

#### GET /api/jobs/{job_id}
Get job status and progress.

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "progress": 100,
  "video_url": "/api/videos/550e8400-e29b-41d4-a716-446655440000"
}
```

#### GET /api/videos/{video_id}
Download completed video (MP4 file).

#### GET /api/health
Health check endpoint.

## Usage Example

```bash
# Generate video from text
curl -X POST http://localhost:8000/api/generate \
  -F "text=Did you know the mitochondria is the powerhouse of the cell?"

# Returns: {"job_id": "abc-123", "status": "queued", "progress": 0}

# Check status
curl http://localhost:8000/api/jobs/abc-123

# Download video when complete
curl http://localhost:8000/api/videos/abc-123 -o video.mp4
```

## Configuration

### TTS Voices

Default voice: `en-US-ChristopherNeural` (male narrator)

Available voices in `pipeline/tts_generator.py`:
- `en-US-ChristopherNeural` - Male, narrative style
- `en-US-JennyNeural` - Female, friendly
- `en-US-GuyNeural` - Male, casual
- `en-US-AriaNeural` - Female, news style

### Video Settings

Edit `pipeline/video_composer.py`:
- Resolution: Default 1080x1920 (9:16 vertical)
- Font size: 60px
- Background: Semi-transparent black box
- FPS: 30

## Development

Run with auto-reload:
```bash
uvicorn main:app --reload
```

## Troubleshooting

### "No gameplay clips found"
Add MP4 files to `../assets/gameplay/` directory:
```bash
mkdir -p ../assets/gameplay
cp your-gameplay.mp4 ../assets/gameplay/
```

### MoviePy errors
Install ffmpeg:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`

### Import errors
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Production Deployment

For production use:
1. Use a proper job queue (Celery + Redis) instead of in-memory jobs
2. Store videos in object storage (S3, GCS) instead of local filesystem
3. Add authentication and rate limiting
4. Configure CORS for your frontend domain
5. Use a reverse proxy (nginx) in front of uvicorn
6. Set up monitoring and logging

## License

MIT
