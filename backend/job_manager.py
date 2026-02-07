"""In-memory job tracking for video generation tasks."""
import asyncio
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from models import JobStatus


class Job:
    """Represents a video generation job."""

    def __init__(self, job_id: str, text: str):
        self.job_id = job_id
        self.text = text
        self.status = JobStatus.QUEUED
        self.progress = 0
        self.video_path: Optional[str] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_progress(self, progress: int, status: Optional[JobStatus] = None):
        """Update job progress and optionally status."""
        self.progress = min(100, max(0, progress))
        if status:
            self.status = status
        self.updated_at = datetime.utcnow()

    def mark_complete(self, video_path: str):
        """Mark job as complete with video path."""
        self.status = JobStatus.COMPLETE
        self.progress = 100
        self.video_path = video_path
        self.updated_at = datetime.utcnow()

    def mark_error(self, error: str):
        """Mark job as failed with error message."""
        self.status = JobStatus.ERROR
        self.error = error
        self.updated_at = datetime.utcnow()


class JobManager:
    """Manages video generation jobs in memory."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, text: str) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid4())
        async with self._lock:
            job = Job(job_id, text)
            self._jobs[job_id] = job
        return job_id

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_job_progress(self, job_id: str, progress: int, status: Optional[JobStatus] = None):
        """Update job progress."""
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update_progress(progress, status)

    async def mark_job_complete(self, job_id: str, video_path: str):
        """Mark job as complete."""
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].mark_complete(video_path)

    async def mark_job_error(self, job_id: str, error: str):
        """Mark job as failed."""
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].mark_error(error)

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        async with self._lock:
            old_job_ids = [
                job_id for job_id, job in self._jobs.items()
                if job.updated_at < cutoff
            ]
            for job_id in old_job_ids:
                del self._jobs[job_id]


# Global job manager instance
job_manager = JobManager()
