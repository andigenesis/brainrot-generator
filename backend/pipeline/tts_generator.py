"""Text-to-speech generation using edge-tts with gTTS fallback."""
import asyncio
import re
from pathlib import Path
from typing import Optional, Dict, List

import edge_tts
from gtts import gTTS
from moviepy.editor import AudioFileClip


async def generate_tts(
    text: str,
    output_path: str,
    voice: str = "en-US-JennyNeural"
) -> Dict[str, any]:
    """
    Generate text-to-speech audio using Microsoft Edge TTS with gTTS fallback.

    Args:
        text: Text to convert to speech
        output_path: Path to save the MP3 file
        voice: Voice to use (default: en-US-JennyNeural)

    Returns:
        Dict with keys:
            - audio_path: Path to the generated audio file
            - timed_segments: List[Dict] with {text, start_ms, end_ms} for each caption segment
            - word_timings: List[Dict] with {word, start_ms, end_ms} for each individual word
              (from edge-tts WordBoundary events; None if gTTS fallback was used)

    Available voices (edge-tts):
        - en-US-ChristopherNeural (male, good for narration)
        - en-US-JennyNeural (female, friendly)
        - en-US-GuyNeural (male, casual)
        - en-US-AriaNeural (female, news style)
    """
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    timed_segments = []
    word_timings = None

    try:
        # Try edge-tts first and extract timing data
        communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
        submaker = edge_tts.SubMaker()

        # Collect raw per-word timing from WordBoundary events
        raw_word_boundaries = []

        # Stream to collect timing data
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)
                # Capture raw per-word timing directly from edge-tts
                raw_word_boundaries.append({
                    "word": chunk["text"],
                    "offset_ms": chunk["offset"] // 10000,  # 100-ns ticks to ms
                    "duration_ms": chunk["duration"] // 10000,
                })
            elif chunk["type"] == "SentenceBoundary":
                submaker.feed(chunk)

        # Save audio
        with open(output_path, "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)

        # Build per-word timing list from raw WordBoundary events
        word_timings = []
        for wb in raw_word_boundaries:
            word_timings.append({
                "word": wb["word"],
                "start_ms": wb["offset_ms"],
                "end_ms": wb["offset_ms"] + wb["duration_ms"],
            })

        # Parse SubMaker subtitles to extract timed segments
        # get_srt() returns one word per cue; group into ~5-word phrases
        subtitle_text = submaker.get_srt()
        word_segments = _parse_srt_to_segments(subtitle_text)
        timed_segments = _group_segments(word_segments, words_per_group=5)

    except Exception as e:
        # Fall back to gTTS if edge-tts fails
        print(f"edge-tts failed ({e}), falling back to gTTS")
        tts = gTTS(text=text, lang='en')
        tts.save(output_path)

        # Estimate timing for gTTS by splitting into sentences
        timed_segments = _estimate_gtts_timing(text, output_path)
        word_timings = None

    return {
        "audio_path": output_path,
        "timed_segments": timed_segments,
        "word_timings": word_timings,
    }


def _parse_srt_to_segments(srt_text: str) -> List[Dict[str, any]]:
    """
    Parse SRT subtitle format to extract timed segments.

    Args:
        srt_text: SRT subtitle file content

    Returns:
        List of dicts with {text, start_ms, end_ms}
    """
    segments = []

    # SRT format: index, timestamp, text, blank line
    # Example:
    # 1
    # 00:00:00,000 --> 00:00:02,500
    # First caption text

    pattern = r'(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})\n(.+?)(?=\n\n|\Z)'

    for match in re.finditer(pattern, srt_text, re.DOTALL):
        start_h, start_m, start_s, start_ms = int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5))
        end_h, end_m, end_s, end_ms = int(match.group(6)), int(match.group(7)), int(match.group(8)), int(match.group(9))
        caption_text = match.group(10).strip()

        start_total_ms = (start_h * 3600 + start_m * 60 + start_s) * 1000 + start_ms
        end_total_ms = (end_h * 3600 + end_m * 60 + end_s) * 1000 + end_ms

        segments.append({
            "text": caption_text,
            "start_ms": start_total_ms,
            "end_ms": end_total_ms
        })

    return segments


def _group_segments(
    segments: List[Dict[str, any]], words_per_group: int = 5
) -> List[Dict[str, any]]:
    """
    Split segments into phrases of ~words_per_group words.

    Each input segment may contain one word or a full sentence.
    Words within a segment get proportional timing based on character length.
    """
    if not segments:
        return segments

    # First, expand each segment into individual words with proportional timing
    word_segments = []
    for seg in segments:
        words = seg["text"].split()
        if not words:
            continue
        if len(words) == 1:
            word_segments.append(seg)
            continue
        # Distribute segment duration proportionally by character length
        total_chars = sum(len(w) for w in words)
        seg_start = seg["start_ms"]
        seg_duration = seg["end_ms"] - seg["start_ms"]
        current = seg_start
        for w in words:
            w_duration = seg_duration * len(w) / total_chars
            word_segments.append({
                "text": w,
                "start_ms": current,
                "end_ms": current + w_duration,
            })
            current += w_duration

    # Now group individual words into ~words_per_group phrases
    grouped = []
    buf_texts = []
    buf_start = word_segments[0]["start_ms"] if word_segments else 0
    buf_end = buf_start

    for ws in word_segments:
        if not buf_texts:
            buf_start = ws["start_ms"]
        buf_texts.append(ws["text"])
        buf_end = ws["end_ms"]

        if len(buf_texts) >= words_per_group:
            grouped.append({
                "text": " ".join(buf_texts),
                "start_ms": int(buf_start),
                "end_ms": int(buf_end),
            })
            buf_texts = []

    # Flush remaining words
    if buf_texts:
        grouped.append({
            "text": " ".join(buf_texts),
            "start_ms": int(buf_start),
            "end_ms": int(buf_end),
        })

    return grouped


def _estimate_gtts_timing(text: str, audio_path: str) -> List[Dict[str, any]]:
    """
    Estimate timing for gTTS by splitting text into sentences.

    Args:
        text: Full text content
        audio_path: Path to generated audio file

    Returns:
        List of dicts with {text, start_ms, end_ms}
    """
    # Get audio duration using moviepy
    audio = AudioFileClip(audio_path)
    total_duration_ms = int(audio.duration * 1000)
    audio.close()

    # Split text into sentences
    sentences = re.split(r'[.!?]+\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [{
            "text": text,
            "start_ms": 0,
            "end_ms": total_duration_ms
        }]

    # Calculate character count for proportional distribution
    char_counts = [len(s) for s in sentences]
    total_chars = sum(char_counts)

    # Distribute duration proportionally based on character count
    segments = []
    current_time = 0

    for sentence, char_count in zip(sentences, char_counts):
        duration = int((char_count / total_chars) * total_duration_ms)
        segments.append({
            "text": sentence,
            "start_ms": current_time,
            "end_ms": current_time + duration
        })
        current_time += duration

    # Adjust last segment to match exact audio duration
    if segments:
        segments[-1]["end_ms"] = total_duration_ms

    return segments


async def list_available_voices() -> list:
    """
    Get list of available voices from edge-tts.

    Returns:
        List of voice dictionaries with name, gender, locale info
    """
    voices = await edge_tts.list_voices()
    # Filter to English voices only
    return [v for v in voices if v["Locale"].startswith("en-")]
