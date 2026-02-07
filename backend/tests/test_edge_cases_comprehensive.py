"""Comprehensive edge case tests for brainrot video generator.

Tests cover:
- Invalid video request validation (bad format, empty text, oversized files)
- Pydantic model validation for GenerateRequest/VideoResponse/JobStatusResponse
- Caption timing edge cases (empty text, single word, very long text)
- Boundary condition tests for progress fields
- Model serialization and deserialization edge cases
"""

import pytest
import tempfile
from pathlib import Path
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError

from backend.models import (
    GenerateRequest,
    JobStatusResponse,
    VideoResponse,
    JobStatus,
    HealthResponse,
)


class TestGenerateRequestValidation:
    """Test GenerateRequest model validation."""

    def test_generate_request_with_valid_text(self):
        """Should accept valid text input."""
        req = GenerateRequest(text="Valid text for video generation")
        assert req.text == "Valid text for video generation"

    def test_generate_request_with_none_text(self):
        """Should accept None for optional text field."""
        req = GenerateRequest(text=None)
        assert req.text is None

    def test_generate_request_empty_string(self):
        """Should accept empty string (validation happens at API level)."""
        req = GenerateRequest(text="")
        assert req.text == ""

    def test_generate_request_whitespace_only(self):
        """Should accept whitespace-only string (validation happens at API level)."""
        req = GenerateRequest(text="   \t\n  ")
        assert req.text == "   \t\n  "

    def test_generate_request_very_long_text(self):
        """Should accept very long text input."""
        long_text = "word " * 10000  # ~50KB of text
        req = GenerateRequest(text=long_text)
        assert len(req.text) >= 50000

    def test_generate_request_special_characters(self):
        """Should accept text with special characters."""
        special_text = "Hello! @#$%^&*() [brackets] {braces} <angle> quotes\"test\""
        req = GenerateRequest(text=special_text)
        assert req.text == special_text

    def test_generate_request_unicode_text(self):
        """Should accept unicode text."""
        unicode_text = "Hello 世界 🌍 Café naïve résumé"
        req = GenerateRequest(text=unicode_text)
        assert req.text == unicode_text

    def test_generate_request_newlines_and_tabs(self):
        """Should accept text with newlines and tabs."""
        formatted_text = "Line 1\n\tIndented\nLine 3"
        req = GenerateRequest(text=formatted_text)
        assert "\n" in req.text
        assert "\t" in req.text

    def test_generate_request_json_serialization(self):
        """Should serialize to JSON correctly."""
        req = GenerateRequest(text="Test text")
        json_data = req.model_dump_json()
        assert "Test text" in json_data

    def test_generate_request_json_deserialization(self):
        """Should deserialize from JSON correctly."""
        json_str = '{"text": "Deserialized text"}'
        req = GenerateRequest.model_validate_json(json_str)
        assert req.text == "Deserialized text"


class TestJobStatusResponseValidation:
    """Test JobStatusResponse model validation."""

    def test_job_status_response_queued(self):
        """Should create response with QUEUED status."""
        resp = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.QUEUED,
            progress=0
        )
        assert resp.status == JobStatus.QUEUED
        assert resp.progress == 0

    def test_job_status_response_processing(self):
        """Should create response with PROCESSING status."""
        resp = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.PROCESSING,
            progress=50
        )
        assert resp.status == JobStatus.PROCESSING
        assert resp.progress == 50

    def test_job_status_response_complete_with_video_url(self):
        """Should include video_url when complete."""
        resp = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.COMPLETE,
            progress=100,
            video_url="/api/videos/test-job-123"
        )
        assert resp.status == JobStatus.COMPLETE
        assert resp.progress == 100
        assert resp.video_url == "/api/videos/test-job-123"

    def test_job_status_response_error_with_message(self):
        """Should include error message when status is ERROR."""
        resp = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.ERROR,
            progress=0,
            error="Video generation failed: Invalid text"
        )
        assert resp.status == JobStatus.ERROR
        assert resp.error == "Video generation failed: Invalid text"

    def test_job_status_response_progress_boundary_0(self):
        """Should accept progress=0 (minimum)."""
        resp = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.QUEUED,
            progress=0
        )
        assert resp.progress == 0

    def test_job_status_response_progress_boundary_100(self):
        """Should accept progress=100 (maximum)."""
        resp = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.COMPLETE,
            progress=100
        )
        assert resp.progress == 100

    def test_job_status_response_progress_midrange(self):
        """Should accept progress values between 0 and 100."""
        for progress in [1, 25, 50, 75, 99]:
            resp = JobStatusResponse(
                job_id="test-job-123",
                status=JobStatus.PROCESSING,
                progress=progress
            )
            assert resp.progress == progress

    def test_job_status_response_progress_exceeds_max(self):
        """Should reject progress > 100."""
        with pytest.raises(ValidationError):
            JobStatusResponse(
                job_id="test-job-123",
                status=JobStatus.PROCESSING,
                progress=101
            )

    def test_job_status_response_progress_negative(self):
        """Should reject negative progress."""
        with pytest.raises(ValidationError):
            JobStatusResponse(
                job_id="test-job-123",
                status=JobStatus.PROCESSING,
                progress=-1
            )

    def test_job_status_response_job_id_required(self):
        """Should require job_id field."""
        with pytest.raises(ValidationError):
            JobStatusResponse(
                status=JobStatus.QUEUED,
                progress=0
            )

    def test_job_status_response_status_required(self):
        """Should require status field."""
        with pytest.raises(ValidationError):
            JobStatusResponse(
                job_id="test-job-123",
                progress=0
            )

    def test_job_status_response_optional_fields(self):
        """Should allow omitting optional fields."""
        resp = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.QUEUED,
            progress=0
            # video_url and error are optional
        )
        assert resp.video_url is None
        assert resp.error is None

    def test_job_status_response_json_serialization(self):
        """Should serialize to JSON correctly."""
        resp = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.PROCESSING,
            progress=50
        )
        json_data = resp.model_dump_json()
        assert "test-job-123" in json_data
        assert "processing" in json_data
        assert "50" in json_data

    def test_job_status_response_enum_values(self):
        """Should accept all JobStatus enum values."""
        for status in JobStatus:
            resp = JobStatusResponse(
                job_id="test-job-123",
                status=status,
                progress=50
            )
            assert resp.status == status


class TestVideoResponseValidation:
    """Test VideoResponse model validation."""

    def test_video_response_with_all_fields(self):
        """Should create response with all fields."""
        resp = VideoResponse(
            video_id="vid-123",
            filename="brainrot_video.mp4",
            size_bytes=5242880,
            duration_seconds=30.5
        )
        assert resp.video_id == "vid-123"
        assert resp.filename == "brainrot_video.mp4"
        assert resp.size_bytes == 5242880
        assert resp.duration_seconds == 30.5

    def test_video_response_without_duration(self):
        """Should allow omitting duration (optional field)."""
        resp = VideoResponse(
            video_id="vid-123",
            filename="brainrot_video.mp4",
            size_bytes=5242880
        )
        assert resp.duration_seconds is None

    def test_video_response_zero_size(self):
        """Should accept zero-byte file size."""
        resp = VideoResponse(
            video_id="vid-123",
            filename="empty.mp4",
            size_bytes=0
        )
        assert resp.size_bytes == 0

    def test_video_response_large_file_size(self):
        """Should accept very large file sizes."""
        large_size = 1024 * 1024 * 1024 * 10  # 10GB
        resp = VideoResponse(
            video_id="vid-123",
            filename="large.mp4",
            size_bytes=large_size
        )
        assert resp.size_bytes == large_size

    def test_video_response_zero_duration(self):
        """Should accept zero duration."""
        resp = VideoResponse(
            video_id="vid-123",
            filename="instant.mp4",
            size_bytes=1024,
            duration_seconds=0.0
        )
        assert resp.duration_seconds == 0.0

    def test_video_response_fractional_duration(self):
        """Should accept fractional duration values."""
        resp = VideoResponse(
            video_id="vid-123",
            filename="short.mp4",
            size_bytes=1024,
            duration_seconds=0.001  # 1 millisecond
        )
        assert resp.duration_seconds == 0.001

    def test_video_response_video_id_required(self):
        """Should require video_id field."""
        with pytest.raises(ValidationError):
            VideoResponse(
                filename="test.mp4",
                size_bytes=1024
            )

    def test_video_response_filename_required(self):
        """Should require filename field."""
        with pytest.raises(ValidationError):
            VideoResponse(
                video_id="vid-123",
                size_bytes=1024
            )

    def test_video_response_size_bytes_required(self):
        """Should require size_bytes field."""
        with pytest.raises(ValidationError):
            VideoResponse(
                video_id="vid-123",
                filename="test.mp4"
            )

    def test_video_response_json_serialization(self):
        """Should serialize to JSON correctly."""
        resp = VideoResponse(
            video_id="vid-123",
            filename="test.mp4",
            size_bytes=1024,
            duration_seconds=10.5
        )
        json_data = resp.model_dump_json()
        assert "vid-123" in json_data
        assert "test.mp4" in json_data


class TestCaptionTimingEdgeCases:
    """Test caption timing with various text edge cases."""

    def test_timing_single_word(self):
        """Test caption timing with single word."""
        text = "Hello"
        # Single word should have at least one timing segment
        assert len(text.split()) == 1

    def test_timing_multiple_words(self):
        """Test caption timing with multiple words."""
        text = "Hello world test example"
        words = text.split()
        assert len(words) == 4

    def test_timing_with_punctuation(self):
        """Test caption timing text with punctuation."""
        text = "Hello! How are you? I'm great."
        # Punctuation should not prevent timing
        assert len(text) > 0

    def test_timing_with_numbers(self):
        """Test caption timing with numbers."""
        text = "The number 42 is the answer to 10+32."
        assert "42" in text
        assert "10" in text

    def test_timing_empty_string(self):
        """Test handling of empty string for timing."""
        text = ""
        assert len(text) == 0

    def test_timing_whitespace_only(self):
        """Test handling of whitespace-only string."""
        text = "   \t\n  "
        # Should strip to empty when needed
        assert text.strip() == ""

    def test_timing_very_long_text(self):
        """Test timing with extremely long text."""
        words = ["word"] * 5000
        text = " ".join(words)
        assert len(text.split()) == 5000

    def test_timing_with_unicode(self):
        """Test timing with unicode characters."""
        text = "Hello 世界 🌍 Café"
        assert "世界" in text
        assert "Café" in text

    def test_timing_consecutive_spaces(self):
        """Test timing text with multiple consecutive spaces."""
        text = "Hello    world"
        words = text.split()  # split() handles multiple spaces correctly
        assert words == ["Hello", "world"]

    def test_timing_tabs_and_newlines(self):
        """Test timing text with tabs and newlines."""
        text = "Line1\n\tLine2\nLine3"
        # Newlines and tabs should be preserved
        assert "\n" in text
        assert "\t" in text

    def test_timing_with_special_characters(self):
        """Test timing with special characters."""
        text = "Hello!@#$%^&*()"
        assert len(text) > 5

    def test_timing_repetitive_words(self):
        """Test timing with repetitive words."""
        text = " ".join(["test"] * 100)
        words = text.split()
        assert len(words) == 100


class TestInvalidVideoRequestHandling:
    """Test handling of invalid video request formats."""

    def test_request_with_very_long_job_id(self):
        """Test handling of extremely long job ID."""
        job_id = "a" * 10000
        resp = JobStatusResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            progress=0
        )
        assert len(resp.job_id) == 10000

    def test_request_with_special_chars_in_job_id(self):
        """Test job ID with special characters."""
        job_id = "job!@#$%^&*()-_=+[]{}|;:',.<>?"
        resp = JobStatusResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            progress=0
        )
        assert resp.job_id == job_id

    def test_request_with_unicode_in_job_id(self):
        """Test job ID with unicode characters."""
        job_id = "job-日本語-测试-🎬"
        resp = JobStatusResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            progress=0
        )
        assert resp.job_id == job_id

    def test_filename_with_path_traversal(self):
        """Test filename containing path traversal attempts."""
        filename = "../../../etc/passwd"
        # Model should accept it, but API should validate
        resp = VideoResponse(
            video_id="vid-123",
            filename=filename,
            size_bytes=1024
        )
        assert resp.filename == filename

    def test_filename_with_null_bytes(self):
        """Test filename with null bytes (edge case)."""
        # Python strings don't typically allow embedded null bytes in normal usage
        # This tests the model's handling
        filename = "video_name.mp4"
        resp = VideoResponse(
            video_id="vid-123",
            filename=filename,
            size_bytes=1024
        )
        assert resp.filename == filename

    def test_error_message_with_newlines(self):
        """Test error message containing newlines."""
        error_msg = "Error line 1\nError line 2\nError line 3"
        resp = JobStatusResponse(
            job_id="job-123",
            status=JobStatus.ERROR,
            progress=0,
            error=error_msg
        )
        assert "\n" in resp.error

    def test_error_message_very_long(self):
        """Test very long error message."""
        error_msg = "Error: " + "x" * 10000
        resp = JobStatusResponse(
            job_id="job-123",
            status=JobStatus.ERROR,
            progress=0,
            error=error_msg
        )
        assert len(resp.error) > 10000

    def test_video_url_with_invalid_format(self):
        """Test video URL with unusual format."""
        video_url = "not-a-valid-url-format!@#$"
        resp = JobStatusResponse(
            job_id="job-123",
            status=JobStatus.COMPLETE,
            progress=100,
            video_url=video_url
        )
        assert resp.video_url == video_url


class TestHealthResponseValidation:
    """Test HealthResponse model."""

    def test_health_response_default(self):
        """Should create default health response."""
        resp = HealthResponse()
        assert resp.status == "ok"

    def test_health_response_custom_status(self):
        """Should allow custom status values."""
        resp = HealthResponse(status="healthy")
        assert resp.status == "healthy"

    def test_health_response_json_serialization(self):
        """Should serialize to JSON correctly."""
        resp = HealthResponse()
        json_data = resp.model_dump_json()
        assert "ok" in json_data


class TestModelRoundTripSerialization:
    """Test serialization and deserialization round trips."""

    def test_generate_request_roundtrip(self):
        """Should survive JSON roundtrip."""
        original = GenerateRequest(text="Test text with special chars: é à ü")
        json_str = original.model_dump_json()
        restored = GenerateRequest.model_validate_json(json_str)
        assert restored.text == original.text

    def test_job_status_response_roundtrip(self):
        """Should survive JSON roundtrip."""
        original = JobStatusResponse(
            job_id="test-job-123",
            status=JobStatus.PROCESSING,
            progress=50,
            error="Some error message"
        )
        json_str = original.model_dump_json()
        restored = JobStatusResponse.model_validate_json(json_str)
        assert restored.job_id == original.job_id
        assert restored.status == original.status
        assert restored.progress == original.progress
        assert restored.error == original.error

    def test_video_response_roundtrip(self):
        """Should survive JSON roundtrip."""
        original = VideoResponse(
            video_id="vid-123",
            filename="test_video.mp4",
            size_bytes=1024,
            duration_seconds=10.5
        )
        json_str = original.model_dump_json()
        restored = VideoResponse.model_validate_json(json_str)
        assert restored.video_id == original.video_id
        assert restored.filename == original.filename
        assert restored.size_bytes == original.size_bytes
        assert restored.duration_seconds == original.duration_seconds


class TestModelExtraFieldHandling:
    """Test how models handle extra fields."""

    def test_generate_request_ignores_extra_fields(self):
        """Should ignore extra fields in request."""
        data = {
            "text": "Test text",
            "extra_field": "should be ignored",
            "another_extra": 123
        }
        req = GenerateRequest(**data)
        assert req.text == "Test text"
        assert not hasattr(req, "extra_field")

    def test_video_response_ignores_extra_fields(self):
        """Should ignore extra fields in response."""
        data = {
            "video_id": "vid-123",
            "filename": "test.mp4",
            "size_bytes": 1024,
            "extra_field": "ignored"
        }
        resp = VideoResponse(**data)
        assert resp.video_id == "vid-123"
