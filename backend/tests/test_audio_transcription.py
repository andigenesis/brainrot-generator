"""Tests for audio transcription (Whisper STT) in input_processor.

Tests cover:
- Audio file extension detection
- Whisper transcription mocking
- FFmpeg conversion for non-WAV formats
- Error handling for missing whisper, empty audio, bad files
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import subprocess

from backend.pipeline.input_processor import (
    extract_text,
    _transcribe_audio,
    AUDIO_EXTENSIONS,
)


class TestAudioExtensionDetection:
    """Test that audio file extensions are correctly routed to transcription."""

    @pytest.mark.parametrize("ext", [".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac"])
    def test_audio_extension_in_set(self, ext):
        """All supported audio extensions should be in AUDIO_EXTENSIONS."""
        assert ext in AUDIO_EXTENSIONS

    @pytest.mark.parametrize("filename", [
        "recording.mp3", "voice.wav", "memo.m4a", "audio.ogg",
        "recording.webm", "test.flac", "voice.aac",
    ])
    @patch("backend.pipeline.input_processor._transcribe_audio")
    def test_extract_text_routes_audio_to_transcription(self, mock_transcribe, filename):
        """extract_text should route audio files to _transcribe_audio."""
        mock_transcribe.return_value = "Transcribed text"
        result = extract_text(b"audio bytes", filename)
        assert result == "Transcribed text"
        mock_transcribe.assert_called_once_with(b"audio bytes", filename)

    def test_extract_text_rejects_unknown_format(self):
        """extract_text should raise ValueError for unsupported formats."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text(b"data", "test.xyz")


class TestAudioTranscription:
    """Test the _transcribe_audio function with mocked Whisper."""

    @patch("backend.pipeline.input_processor.subprocess.run")
    def test_transcribe_wav_skips_conversion(self, mock_run):
        """WAV files should skip ffmpeg conversion."""
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Hello world"}
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            # Re-import to pick up mocked whisper
            import importlib
            import backend.pipeline.input_processor as mod
            importlib.reload(mod)

            result = mod._transcribe_audio(b"wav audio data", "recording.wav")

        assert result == "Hello world"
        # ffmpeg should NOT be called for WAV
        mock_run.assert_not_called()

    @patch("backend.pipeline.input_processor.subprocess.run")
    def test_transcribe_mp3_converts_to_wav(self, mock_run):
        """Non-WAV files should be converted via ffmpeg."""
        mock_run.return_value = Mock(returncode=0)

        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Transcribed from MP3"}
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            import importlib
            import backend.pipeline.input_processor as mod
            importlib.reload(mod)

            result = mod._transcribe_audio(b"mp3 audio data", "recording.mp3")

        assert result == "Transcribed from MP3"
        # ffmpeg should be called for MP3→WAV conversion
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"

    @patch("backend.pipeline.input_processor.subprocess.run")
    def test_transcribe_webm_from_browser(self, mock_run):
        """WebM files from browser recording should be converted and transcribed."""
        mock_run.return_value = Mock(returncode=0)

        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Browser voice input"}
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            import importlib
            import backend.pipeline.input_processor as mod
            importlib.reload(mod)

            result = mod._transcribe_audio(b"webm audio data", "recording.webm")

        assert result == "Browser voice input"

    @patch("backend.pipeline.input_processor.subprocess.run")
    def test_transcribe_empty_audio_raises(self, mock_run):
        """Empty transcription result should raise ValueError."""
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": ""}
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            import importlib
            import backend.pipeline.input_processor as mod
            importlib.reload(mod)

            with pytest.raises(ValueError, match="No speech detected"):
                mod._transcribe_audio(b"silent audio", "silence.wav")

    @patch("backend.pipeline.input_processor.subprocess.run")
    def test_ffmpeg_failure_raises(self, mock_run):
        """FFmpeg conversion failure should raise ValueError."""
        mock_run.return_value = Mock(returncode=1, stderr="codec error")

        with pytest.raises(ValueError, match="Audio conversion failed"):
            _transcribe_audio(b"bad audio", "bad.mp3")

    def test_whisper_not_installed_raises(self):
        """Missing whisper package should raise clear error."""
        with patch.dict("sys.modules", {"whisper": None}):
            with patch("backend.pipeline.input_processor.subprocess.run") as mock_run:
                # For WAV, no ffmpeg needed
                with pytest.raises((ValueError, ImportError)):
                    _transcribe_audio(b"audio data", "test.wav")


class TestAudioFileUploadIntegration:
    """Integration tests for audio file upload path."""

    def test_pdf_still_works(self):
        """PDF extraction should still work after adding audio support."""
        # Minimal valid PDF
        from pypdf import PdfWriter
        from io import BytesIO

        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        # Add text to the blank page
        pdf_buffer = BytesIO()
        writer.write(pdf_buffer)
        pdf_bytes = pdf_buffer.getvalue()

        # This should not route to audio transcription
        # (it may raise "No text content" which is expected for blank page)
        with pytest.raises(ValueError, match="No text content found"):
            extract_text(pdf_bytes, "document.pdf")

    def test_txt_still_works(self):
        """TXT extraction should still work after adding audio support."""
        result = extract_text(b"Hello, this is plain text.", "notes.txt")
        assert result == "Hello, this is plain text."
