"""Pydantic models for the brainrot video generator API."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of a video generation job."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class GenerateRequest(BaseModel):
    """Request model for video generation."""
    text: Optional[str] = Field(None, description="Direct text input for video generation")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Did you know that the mitochondria is the powerhouse of the cell?"
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100, description="Progress percentage (0-100)")
    video_url: Optional[str] = Field(None, description="URL to download the video (when complete)")
    error: Optional[str] = Field(None, description="Error message (if status is ERROR)")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "complete",
                "progress": 100,
                "video_url": "/api/videos/550e8400-e29b-41d4-a716-446655440000"
            }
        }


class VideoResponse(BaseModel):
    """Response model for video metadata."""
    video_id: str
    filename: str
    size_bytes: int
    duration_seconds: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "brainrot_video_550e8400.mp4",
                "size_bytes": 5242880,
                "duration_seconds": 30.5
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
