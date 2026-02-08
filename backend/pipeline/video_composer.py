"""Video compositing using MoviePy."""
import logging
import os
import random
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from PIL import Image, ImageDraw, ImageFont
try:
    # moviepy 2.x
    from moviepy import (
        VideoFileClip,
        AudioFileClip,
        ImageClip,
        CompositeVideoClip,
        concatenate_videoclips,
        vfx,
    )
    MOVIEPY_V2 = True
except ImportError:
    # moviepy 1.x
    from moviepy.editor import (
        VideoFileClip,
        AudioFileClip,
        ImageClip,
        CompositeVideoClip,
        concatenate_videoclips,
    )
    from moviepy.video.fx import resize as _resize_mod
    MOVIEPY_V2 = False


def _clip_set_start(clip, t):
    return clip.with_start(t) if MOVIEPY_V2 else clip.set_start(t)


def _clip_set_duration(clip, d):
    return clip.with_duration(d) if MOVIEPY_V2 else clip.set_duration(d)


def _clip_set_position(clip, pos):
    return clip.with_position(pos) if MOVIEPY_V2 else clip.set_position(pos)


def _clip_set_audio(clip, audio):
    return clip.with_audio(audio) if MOVIEPY_V2 else clip.set_audio(audio)


def _clip_subclip(clip, start, end):
    return clip.subclipped(start, end) if MOVIEPY_V2 else clip.subclip(start, end)


def _clip_resize(clip, newsize):
    if MOVIEPY_V2:
        return clip.resized(newsize=newsize)
    return clip.fx(_resize_mod.resize, newsize=newsize)


def _clip_crossfade(clip, fade_duration):
    if MOVIEPY_V2:
        return clip.with_effects([vfx.CrossFadeIn(fade_duration), vfx.CrossFadeOut(fade_duration)])
    return clip.crossfadein(fade_duration).crossfadeout(fade_duration)


def _clip_transform(clip, func):
    return clip.transform(func) if MOVIEPY_V2 else clip.fl(func)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """
    Wrap text to fit within max_width pixels.

    Args:
        text: Text to wrap
        font: PIL font object
        max_width: Maximum width in pixels

    Returns:
        List of text lines
    """
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Single word is too long, add it anyway
                lines.append(word)

    if current_line:
        lines.append(' '.join(current_line))

    return lines


def _create_text_overlay(
    text: str,
    resolution: tuple,
    fontsize: int = 60,
    padding: int = 50
) -> str:
    """
    Create a TikTok-style text overlay image using Pillow (static, for backward compatibility).

    Args:
        text: Text to render
        resolution: Video resolution (width, height)
        fontsize: Font size in pixels
        padding: Horizontal padding in pixels

    Returns:
        Path to temporary PNG file with text overlay
    """
    width, height = resolution

    # Create transparent image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load Montserrat Bold font with fallbacks
    try:
        font = ImageFont.truetype('/opt/andi/projects/brainrot-generator/assets/fonts/Montserrat-Bold.ttf', fontsize)
    except OSError:
        try:
            # Try common bold font paths on macOS
            font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', fontsize)
        except OSError:
            try:
                font = ImageFont.truetype('/Library/Fonts/Arial Bold.ttf', fontsize)
            except OSError:
                try:
                    # Fall back to Helvetica Bold
                    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', fontsize)
                except OSError:
                    # Use default font as last resort
                    font = ImageFont.load_default()

    # Wrap text to fit width
    max_text_width = width - (2 * padding)
    lines = _wrap_text(text, font, max_text_width)

    # Calculate total text block height
    line_height = fontsize + 10  # Add some line spacing
    total_text_height = len(lines) * line_height

    # Calculate starting Y position to center text vertically
    y_start = (height - total_text_height) // 2

    # Draw each line of text with TikTok style (no background box, black outline)
    y_position = y_start
    for line in lines:
        # Get text bounding box to center it horizontally
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x_position = (width - text_width) // 2

        # Draw white text with black outline (TikTok style)
        draw.text(
            (x_position, y_position),
            line,
            fill='white',
            font=font,
            stroke_width=5,
            stroke_fill='black'
        )
        y_position += line_height

    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(temp_file.name, 'PNG')
    temp_file.close()

    return temp_file.name


def _create_timed_captions(
    timed_segments: list,
    resolution: tuple,
    fontsize: int = 52,
    padding: int = 40,
    word_timings: Optional[list] = None
) -> list:
    """
    Create TikTok-style synchronized caption clips with word-by-word yellow highlighting.

    Args:
        timed_segments: List of dicts with {text, start_ms, end_ms}
        resolution: Video resolution (width, height)
        fontsize: Font size in pixels (default: 52 for TikTok style)
        padding: Horizontal padding in pixels
        word_timings: Optional list of dicts with {word, start_ms, end_ms} from edge-tts
                      WordBoundary events. When provided, uses real per-word timing for
                      yellow highlight instead of proportional character estimates.

    Returns:
        List of MoviePy ImageClip objects with timing set
    """
    width, height = resolution
    caption_clips = []
    segment_render_data = []  # Collect per-segment data in first pass, render in second

    # Build a lookup from real word_timings if provided.
    # We consume them sequentially as we iterate through segments.
    real_word_idx = 0

    # Load Montserrat Bold font with fallbacks
    try:
        font = ImageFont.truetype('/opt/andi/projects/brainrot-generator/assets/fonts/Montserrat-Bold.ttf', fontsize)
    except OSError:
        try:
            font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', fontsize)
        except OSError:
            try:
                font = ImageFont.truetype('/Library/Fonts/Arial Bold.ttf', fontsize)
            except OSError:
                try:
                    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', fontsize)
                except OSError:
                    font = ImageFont.load_default()

    for segment in timed_segments:
        segment_text = segment["text"]
        start_s = segment["start_ms"] / 1000.0
        end_s = segment["end_ms"] / 1000.0
        duration = end_s - start_s

        # Wrap text to fit width (max 2 lines for TikTok style)
        max_text_width = width - (2 * padding)
        lines = _wrap_text(segment_text, font, max_text_width)

        # Limit to 2 lines for cleaner TikTok look
        if len(lines) > 2:
            lines = lines[:2]
            # Add ellipsis if truncated
            if not lines[-1].endswith('...'):
                lines[-1] = lines[-1].rstrip() + '...'

        # Calculate text block dimensions
        line_height = fontsize + 10
        total_text_height = len(lines) * line_height

        # Position at bottom 20-25% of screen
        y_start = int(height * 0.75)  # Start at 75% down (bottom 25%)

        # Split segment text into words for timing
        words = segment_text.split()
        if not words:
            continue

        # Build per-word timing: use real edge-tts timing if available, else proportional
        segment_word_timings = []
        if word_timings and real_word_idx < len(word_timings):
            # Use real per-word timing from edge-tts WordBoundary events
            for word in words:
                if real_word_idx < len(word_timings):
                    wt = word_timings[real_word_idx]
                    segment_word_timings.append({
                        'word': word,
                        'start': wt["start_ms"] / 1000.0,
                        'end': wt["end_ms"] / 1000.0,
                    })
                    real_word_idx += 1
                else:
                    # Ran out of real timings — shouldn't happen but fall back gracefully
                    prev_end = segment_word_timings[-1]['end'] if segment_word_timings else start_s
                    segment_word_timings.append({
                        'word': word,
                        'start': prev_end,
                        'end': prev_end + 0.1,
                    })
        else:
            # Fallback: proportional timing based on character length
            total_chars = sum(len(w) for w in words)
            current_time = start_s
            for word in words:
                word_duration = (len(word) / total_chars) * duration if total_chars > 0 else duration / len(words)
                segment_word_timings.append({
                    'word': word,
                    'start': current_time,
                    'end': current_time + word_duration,
                })
                current_time += word_duration

        # Collect word render data for this segment (image generation + timing computed later)
        segment_render_data.append({
            'lines': lines,
            'y_start': y_start,
            'word_timings': segment_word_timings,
        })

    # Second pass: compute extended durations so each word clip persists until the
    # next word starts (eliminating gaps when TTS is silent between words).
    # Flatten all word timings across segments for cross-segment bridging.
    all_words_flat = []  # list of (segment_idx, word_idx_in_segment, word_timing)
    for seg_idx, seg_data in enumerate(segment_render_data):
        for w_idx, wt in enumerate(seg_data['word_timings']):
            all_words_flat.append((seg_idx, w_idx, wt))

    for flat_idx, (seg_idx, word_idx, word_timing) in enumerate(all_words_flat):
        seg_data = segment_render_data[seg_idx]
        lines = seg_data['lines']
        y_start = seg_data['y_start']

        # Compute clip duration: extend to next word's start to bridge silence gaps
        if flat_idx < len(all_words_flat) - 1:
            # Not the last word overall — extend to when the next word starts
            _, _, next_wt = all_words_flat[flat_idx + 1]
            word_clip_duration = next_wt['start'] - word_timing['start']
        else:
            # Very last word in the entire video — extend 1.5s past its natural end
            word_clip_duration = (word_timing['end'] - word_timing['start']) + 1.5

        # Ensure minimum duration to avoid zero-length clips
        word_clip_duration = max(word_clip_duration, 0.05)

        # Create transparent image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw each line of text with word-by-word coloring
        y_position = y_start
        words_before = 0
        for line_idx, line in enumerate(lines):
            line_words = line.split()

            # Calculate total line width to center it
            total_line_width = 0
            word_widths = []
            for w in line_words:
                bbox = font.getbbox(w)
                w_width = bbox[2] - bbox[0]
                word_widths.append(w_width)
                total_line_width += w_width

            # Add space widths
            space_bbox = font.getbbox(' ')
            space_width = space_bbox[2] - space_bbox[0]
            if len(line_words) > 1:
                total_line_width += space_width * (len(line_words) - 1)

            # Start x position to center the line
            x_position = (width - total_line_width) // 2

            # Draw each word in the line
            for w_idx, word in enumerate(line_words):
                word_global_idx = words_before + w_idx

                # Determine color: yellow for current word, white for others
                if word_global_idx == word_idx:
                    color = '#FFFF00'  # Yellow for current word
                else:
                    color = 'white'

                # Draw text with black outline (TikTok style)
                draw.text(
                    (x_position, y_position),
                    word,
                    fill=color,
                    font=font,
                    stroke_width=5,
                    stroke_fill='black'
                )

                # Move x position for next word
                x_position += word_widths[w_idx] + space_width

            words_before += len(line_words)
            y_position += line_height

        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name, 'PNG')
        temp_file.close()

        # Create ImageClip with extended timing for continuous caption visibility
        clip = ImageClip(temp_file.name)
        clip = _clip_set_duration(_clip_set_start(clip, word_timing['start']), word_clip_duration)
        clip = _clip_set_position(clip, 'center')

        caption_clips.append({
            'clip': clip,
            'temp_file': temp_file.name
        })

    return caption_clips


def _create_diagram_overlays(
    diagram_timings: list[dict],
    resolution: tuple,
    video_duration: float
) -> list:
    """
    Create diagram overlay clips with fade in/out and positioning.

    Args:
        diagram_timings: List of {png_path, start_s, duration_s, label} dicts
        resolution: Video resolution (width, height)
        video_duration: Total video duration to ensure clips don't exceed

    Returns:
        List of dicts with {clip, temp_file} for diagram overlays
    """
    width, height = resolution
    diagram_clips = []

    for diagram in diagram_timings:
        png_path = diagram["png_path"]
        start_s = diagram["start_s"]
        duration_s = min(diagram["duration_s"], video_duration - start_s)

        if duration_s <= 0:
            continue

        # Load diagram image
        diagram_img = Image.open(png_path)

        # Resize to 70% of screen width while maintaining aspect ratio
        target_width = int(width * 0.7)
        aspect_ratio = diagram_img.height / diagram_img.width
        target_height = int(target_width * aspect_ratio)

        # Ensure diagram fits in upper 60% of screen
        max_height = int(height * 0.6)
        if target_height > max_height:
            target_height = max_height
            target_width = int(target_height / aspect_ratio)

        diagram_img = diagram_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # Create temporary file for resized diagram
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        diagram_img.save(temp_file.name, 'PNG')
        temp_file.close()

        # Create ImageClip
        clip = ImageClip(temp_file.name)
        clip = _clip_set_duration(_clip_set_start(clip, start_s), duration_s)

        # Position: centered horizontally, in upper 60% (at 30% from top)
        clip = _clip_set_position(clip, ('center', int(height * 0.15)))

        # Add fade in/out (0.5s each, if duration allows)
        fade_duration = min(0.5, duration_s / 3)
        if duration_s > fade_duration * 2:
            clip = _clip_crossfade(clip, fade_duration)

        diagram_clips.append({
            'clip': clip,
            'temp_file': temp_file.name
        })

    return diagram_clips


def compose_video(
    text: str,
    audio_path: str,
    gameplay_clip_path: str,
    output_path: str,
    resolution: tuple = (1080, 1920),  # 9:16 vertical
    caption_duration: Optional[float] = None,
    timed_segments: Optional[list] = None,
    word_timings: Optional[list] = None,
    diagram_timings: Optional[list] = None
) -> str:
    """
    Compose a brainrot-style video with gameplay background and captions.

    Args:
        text: Caption text to overlay (used if timed_segments is None)
        audio_path: Path to TTS audio file
        gameplay_clip_path: Path to background gameplay video
        output_path: Path to save output video
        resolution: Output resolution (width, height), default 1080x1920
        caption_duration: Duration to show caption (default: use audio duration)
        timed_segments: Optional list of dicts with {text, start_ms, end_ms} for synchronized captions
        word_timings: Optional list of dicts with {word, start_ms, end_ms} for per-word highlight timing
        diagram_timings: Optional list of dicts with {png_path, start_s, duration_s, label} for architecture diagrams

    Returns:
        Path to the generated video file
    """
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Load audio to get duration
    audio = AudioFileClip(audio_path)
    video_duration = caption_duration or audio.duration

    # Load and prepare gameplay clip
    gameplay = VideoFileClip(gameplay_clip_path)

    # If gameplay is shorter than needed, loop it
    if gameplay.duration < video_duration:
        loops_needed = int(video_duration / gameplay.duration) + 1
        gameplay = concatenate_videoclips([gameplay] * loops_needed)

    # Trim to exact duration
    gameplay = _clip_subclip(gameplay, 0, video_duration)

    # Resize gameplay to target resolution (9:16) only if needed
    if gameplay.size != resolution:
        gameplay = _clip_resize(gameplay, newsize=resolution)

    # Create captions - either timed or static
    temp_files_to_cleanup = []

    if timed_segments and len(timed_segments) > 0:
        # Use synchronized line-by-line captions
        caption_data = _create_timed_captions(timed_segments, resolution, word_timings=word_timings)
        caption_clips = [item['clip'] for item in caption_data]
        temp_files_to_cleanup = [item['temp_file'] for item in caption_data]
    else:
        # Fall back to static overlay (backward compatibility)
        caption_image_path = _create_text_overlay(text, resolution)
        temp_files_to_cleanup.append(caption_image_path)

        # Load the text overlay as an ImageClip
        caption = ImageClip(caption_image_path)
        caption = _clip_set_duration(caption, video_duration)
        caption = _clip_set_position(caption, 'center')
        caption_clips = [caption]

    # Create diagram overlays if provided
    diagram_clips = []
    if diagram_timings and len(diagram_timings) > 0:
        diagram_data = _create_diagram_overlays(diagram_timings, resolution, video_duration)
        diagram_clips = [item['clip'] for item in diagram_data]
        temp_files_to_cleanup.extend([item['temp_file'] for item in diagram_data])

        # Add dimming to gameplay during diagram display
        # Create a function to dim the frame during diagram times
        def apply_dimming(get_frame, t):
            """Dim the frame to 50% opacity when a diagram is showing."""
            frame = get_frame(t)
            # Check if any diagram is active at time t
            for diagram in diagram_timings:
                if diagram["start_s"] <= t < (diagram["start_s"] + diagram["duration_s"]):
                    # Apply 50% dimming
                    return (frame * 0.5).astype('uint8')
            return frame

        gameplay = _clip_transform(gameplay, apply_dimming)

    # Composite video: gameplay (dimmed during diagrams) -> diagrams -> captions (always on top)
    # Layer order matters: earlier elements are below later elements
    final_video = CompositeVideoClip([gameplay] + diagram_clips + caption_clips)

    # Set audio
    final_video = _clip_set_audio(final_video, audio)

    # Write output file with retry on broken pipe
    try:
        try:
            final_video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                preset='ultrafast',
                threads=2
            )
        except (BrokenPipeError, OSError) as e:
            logger.exception(
                "write_videofile failed (preset=medium), retrying with ultrafast: %s", e
            )
            # Retry once with ultrafast preset (less ffmpeg buffering)
            final_video.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset='ultrafast',
                threads=2
            )
    finally:
        # Ensure all clips are closed even on failure
        for clip_obj in (audio, gameplay, final_video):
            try:
                clip_obj.close()
            except Exception:
                pass

        # Remove temporary caption image files
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except OSError:
                pass

    return output_path


def get_random_gameplay_clip(gameplay_dir: str = "assets/gameplay") -> Optional[str]:
    """
    Get a random gameplay clip from the assets directory.

    Args:
        gameplay_dir: Directory containing gameplay video files

    Returns:
        Path to a random gameplay clip, or None if directory is empty
    """
    gameplay_path = Path(gameplay_dir)
    if not gameplay_path.exists():
        return None

    # Find all MP4 files
    clips = list(gameplay_path.glob("*.mp4")) + list(gameplay_path.glob("*.MP4"))

    if not clips:
        return None

    return str(random.choice(clips))
