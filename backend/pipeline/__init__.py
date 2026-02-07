"""Video generation pipeline modules."""
# Fix Pillow 10+ compatibility with MoviePy 1.0.3
# MoviePy uses Image.ANTIALIAS which was removed in Pillow 10 (renamed to LANCZOS)
import PIL.Image
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from .tts_generator import generate_tts
from .video_composer import compose_video, get_random_gameplay_clip
from .input_processor import extract_text
from .script_transformer import transform_to_brainrot
from .diagram_generator import (
    extract_mermaid_blocks,
    generate_mermaid_with_llm,
    render_mermaid_to_png,
    find_diagram_timestamps,
    generate_diagram_overlays
)

__all__ = [
    "generate_tts",
    "compose_video",
    "get_random_gameplay_clip",
    "extract_text",
    "transform_to_brainrot",
    "extract_mermaid_blocks",
    "generate_mermaid_with_llm",
    "render_mermaid_to_png",
    "find_diagram_timestamps",
    "generate_diagram_overlays",
]
