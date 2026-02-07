#!/usr/bin/env python3
"""Quick test to verify all imports work correctly."""

def test_imports():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")

    # Test models
    print("  ✓ Importing models...")
    from models import (
        JobStatus,
        GenerateRequest,
        JobStatusResponse,
        VideoResponse,
        HealthResponse
    )

    # Test job manager
    print("  ✓ Importing job_manager...")
    from job_manager import JobManager, job_manager

    # Test pipeline modules
    print("  ✓ Importing pipeline...")
    from pipeline import generate_tts, compose_video, extract_text, get_random_gameplay_clip
    from pipeline.tts_generator import list_available_voices
    from pipeline.video_composer import get_random_gameplay_clip
    from pipeline.input_processor import extract_text

    # Test main app
    print("  ✓ Importing main app...")
    from main import app

    print("\n✅ All imports successful!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Add gameplay clips: mkdir -p ../assets/gameplay && cp *.mp4 ../assets/gameplay/")
    print("3. Run server: uvicorn main:app --reload")
    print("4. Visit http://localhost:8000/docs for API documentation")

if __name__ == "__main__":
    test_imports()
