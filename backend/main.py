"""FastAPI backend for brainrot video generator."""
import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import aiofiles

from models import (
    JobStatusResponse,
    HealthResponse,
    JobStatus,
    GenerateRequest
)
from job_manager import job_manager
from pipeline import (
    generate_tts,
    compose_video,
    extract_text,
    get_random_gameplay_clip,
    transform_to_brainrot,
    generate_diagram_overlays
)


# Initialize FastAPI app
app = FastAPI(
    title="Brainrot Video Generator API",
    description="Convert text into TikTok-style brainrot videos with gameplay backgrounds",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure paths (support env vars for Docker deployment)
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", str(BASE_DIR / "output")))
TEMP_DIR = Path(os.environ.get("TEMP_DIR", str(BASE_DIR / "temp")))
GAMEPLAY_DIR = Path(os.environ.get("GAMEPLAY_DIR", str(BASE_DIR.parent / "assets" / "gameplay")))

# Static files directory (pre-built frontend)
STATIC_DIR = Path(os.environ.get("STATIC_DIR", str(BASE_DIR.parent / "frontend" / "dist")))

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


async def process_video_generation(job_id: str, text: str, transform: bool = True, diagrams: bool = True):
    """
    Background task to process video generation pipeline.

    Steps:
        1. Update status to PROCESSING
        2. Transform text to brainrot narration (if transform=True, progress 10%)
        3. Generate TTS audio with timing data (progress 30%)
        4. Generate diagram overlays if enabled (progress 40%)
        5. Select random gameplay clip (progress 50%)
        6. Compose video with synchronized captions and diagrams (progress 60-90%)
        7. Save video and mark complete (progress 100%)
    """
    try:
        # Update to processing
        await job_manager.update_job_progress(job_id, 5, JobStatus.PROCESSING)

        # Transform text to brainrot narration via LLM
        if transform:
            text = await transform_to_brainrot(text)
        await job_manager.update_job_progress(job_id, 10)

        # Generate TTS audio with timing data
        audio_path = str(TEMP_DIR / f"{job_id}.mp3")
        tts_result = await generate_tts(text, audio_path)
        await job_manager.update_job_progress(job_id, 30)

        # Generate diagram overlays if enabled
        diagram_timings = []
        if diagrams and tts_result.get("word_timings"):
            diagram_timings = await generate_diagram_overlays(
                text,
                tts_result["word_timings"],
                TEMP_DIR
            )
        await job_manager.update_job_progress(job_id, 40)

        # Select gameplay clip
        gameplay_clip = get_random_gameplay_clip(str(GAMEPLAY_DIR))
        if not gameplay_clip:
            raise ValueError(
                "No gameplay clips found in assets/gameplay/. "
                "Please add MP4 files to the gameplay directory."
            )
        await job_manager.update_job_progress(job_id, 50)

        # Compose video with synchronized captions and diagrams (this is the slow part)
        output_path = str(OUTPUT_DIR / f"{job_id}.mp4")
        await asyncio.to_thread(
            compose_video,
            text,
            tts_result["audio_path"],
            gameplay_clip,
            output_path,
            timed_segments=tts_result.get("timed_segments"),
            word_timings=tts_result.get("word_timings"),
            diagram_timings=diagram_timings,
        )
        await job_manager.update_job_progress(job_id, 95)

        # Mark complete
        await job_manager.mark_job_complete(job_id, output_path)

        # Cleanup temp audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)

    except Exception as e:
        error_msg = f"Video generation failed: {str(e)}"
        await job_manager.mark_job_error(job_id, error_msg)


@app.post("/api/generate", response_model=JobStatusResponse)
async def generate_video(
    background_tasks: BackgroundTasks,
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    transform: bool = Form(True),
    diagrams: bool = Form(True),
):
    """
    Start a new video generation job.

    Accepts either direct text input or file upload.
    For file uploads, text is extracted from PDF or TXT files.
    """
    # Validate input
    if not text and not file:
        raise HTTPException(
            status_code=400,
            detail="Either 'text' or 'file' must be provided"
        )

    # Extract text from file if provided
    if file:
        file_bytes = await file.read()
        try:
            text = extract_text(file_bytes, file.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Validate text content
    if not text or not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text content is empty"
        )

    # Create job
    job_id = await job_manager.create_job(text.strip())

    # Start background processing
    background_tasks.add_task(process_video_generation, job_id, text.strip(), transform, diagrams)

    return JobStatusResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        progress=0
    )


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a video generation job.

    Poll this endpoint to track progress.
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    video_url = None
    if job.status == JobStatus.COMPLETE and job.video_path:
        video_url = f"/api/videos/{job_id}"

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        video_url=video_url,
        error=job.error
    )


@app.get("/api/videos/{video_id}")
async def download_video(video_id: str):
    """
    Download a completed video file.

    Returns MP4 file for download.
    """
    job = await job_manager.get_job(video_id)

    if not job:
        raise HTTPException(status_code=404, detail="Video not found")

    if job.status != JobStatus.COMPLETE or not job.video_path:
        raise HTTPException(
            status_code=400,
            detail=f"Video is not ready. Current status: {job.status}"
        )

    if not os.path.exists(job.video_path):
        raise HTTPException(
            status_code=500,
            detail="Video file not found on server"
        )

    return FileResponse(
        job.video_path,
        media_type="video/mp4",
        filename=f"brainrot_{video_id}.mp4"
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.on_event("startup")
async def startup_event():
    """Run startup tasks."""
    print("🎬 Brainrot Video Generator API starting...")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"📁 Gameplay directory: {GAMEPLAY_DIR}")

    # Check for gameplay clips
    if GAMEPLAY_DIR.exists():
        clips = list(GAMEPLAY_DIR.glob("*.mp4")) + list(GAMEPLAY_DIR.glob("*.MP4"))
        print(f"🎮 Found {len(clips)} gameplay clips")
    else:
        print("⚠️  Warning: No gameplay directory found. Create assets/gameplay/ and add MP4 files.")


@app.on_event("shutdown")
async def shutdown_event():
    """Run shutdown tasks."""
    print("👋 Brainrot Video Generator API shutting down...")


# Serve frontend static files (must be after API routes)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the SPA frontend for any non-API route."""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return HTMLResponse(index_path.read_text())
        raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
