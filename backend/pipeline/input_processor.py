"""Input processing: extract text from uploaded files and audio."""
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from pypdf import PdfReader

# Audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.webm', '.flac', '.aac'}


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from uploaded file.

    Supported formats:
        - PDF (.pdf)
        - Plain text (.txt)
        - Audio (.mp3, .wav, .m4a, .ogg, .webm, .flac, .aac) — transcribed via Whisper

    Args:
        file_bytes: File content as bytes
        filename: Original filename (used to determine file type)

    Returns:
        Extracted text content

    Raises:
        ValueError: If file format is not supported
    """
    filename_lower = filename.lower()
    ext = Path(filename_lower).suffix

    # PDF files
    if ext == '.pdf':
        return _extract_pdf_text(file_bytes)

    # Plain text files
    elif ext == '.txt':
        return _extract_plain_text(file_bytes)

    # Audio files — transcribe with Whisper
    elif ext in AUDIO_EXTENSIONS:
        return _transcribe_audio(file_bytes, filename)

    else:
        raise ValueError(
            f"Unsupported file format: {filename}. "
            "Supported formats: .pdf, .txt, .mp3, .wav, .m4a, .ogg, .webm"
        )


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF file."""
    pdf_file = BytesIO(file_bytes)
    reader = PdfReader(pdf_file)

    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)

    if not text_parts:
        raise ValueError("No text content found in PDF")

    return "\n".join(text_parts)


def _extract_plain_text(file_bytes: bytes) -> str:
    """Extract text from plain text file."""
    # Try UTF-8 first, fall back to latin-1
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return file_bytes.decode('latin-1')


def _transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """Transcribe audio file to text using OpenAI Whisper."""
    ext = Path(filename).suffix.lower()

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # Convert to WAV if needed (Whisper works best with WAV)
        wav_path = tmp_path
        if ext != '.wav':
            wav_path = tmp_path + '.wav'
            result = subprocess.run(
                ['ffmpeg', '-i', tmp_path, '-ar', '16000', '-ac', '1', '-y', wav_path],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                raise ValueError(f"Audio conversion failed: {result.stderr[:200]}")

        # Transcribe with Whisper
        try:
            import whisper
        except ImportError:
            raise ValueError(
                "Audio transcription requires openai-whisper. "
                "Install with: pip install openai-whisper"
            )

        model = whisper.load_model("base")
        result = model.transcribe(wav_path, language="en")
        text = result.get("text", "").strip()

        if not text:
            raise ValueError("No speech detected in audio file")

        return text

    finally:
        # Cleanup temp files
        import os
        os.unlink(tmp_path)
        if wav_path != tmp_path and os.path.exists(wav_path):
            os.unlink(wav_path)
