#!/usr/bin/env python3
"""Generate brainrot video for the entity cache tech design with enhanced narration."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from pipeline import (
    generate_tts,
    compose_video,
    get_random_gameplay_clip,
    generate_diagram_overlays,
)
from pipeline.script_transformer import transform_to_brainrot

TEMP_DIR = backend_dir / "temp"
OUTPUT_DIR = backend_dir / "output"
GAMEPLAY_DIR = Path(__file__).parent / "assets" / "gameplay"

TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


async def main():
    # Step 1: Read the source tech design
    input_path = Path(__file__).parent / "test_inputs" / "caching_tech_design.txt"
    raw_text = input_path.read_text()
    print(f"Read source text ({len(raw_text)} chars)")

    # Step 2: Transform to brainrot narration via LLM
    print("\nTransforming to brainrot narration via Ollama...")
    narration = await transform_to_brainrot(raw_text)
    print(f"Narration generated ({len(narration)} chars):")
    print("-" * 60)
    print(narration)
    print("-" * 60)

    # Save narration for inspection
    narration_path = TEMP_DIR / "cache_narration.txt"
    narration_path.write_text(narration)
    print(f"\nSaved narration to {narration_path}")

    # Step 3: Generate TTS with word-level timing (use GuyNeural for TikTok energy)
    print("\nGenerating TTS audio with word timings...")
    audio_path = str(TEMP_DIR / "cache_brainrot.mp3")
    tts_result = await generate_tts(narration, audio_path, voice="en-US-GuyNeural")

    duration = 0.0
    if tts_result["word_timings"]:
        last_word = tts_result["word_timings"][-1]
        duration = last_word["end_ms"] / 1000.0
    print(f"TTS generated: {duration:.2f}s, {len(tts_result['word_timings'] or [])} words")

    # Step 4: Generate diagram overlays from ORIGINAL tech text (has better keywords)
    print("\nGenerating diagram overlays...")
    diagram_timings = await generate_diagram_overlays(
        raw_text,
        tts_result["word_timings"],
        TEMP_DIR,
    )
    print(f"Generated {len(diagram_timings)} diagram overlay(s)")
    for i, d in enumerate(diagram_timings):
        print(f"  [{i}] {d['label']} at {d['start_s']:.1f}s for {d['duration_s']:.1f}s")

    # Step 5: Select gameplay clip
    print("\nSelecting gameplay clip...")
    gameplay_clip = get_random_gameplay_clip(str(GAMEPLAY_DIR))
    print(f"Using: {gameplay_clip}")

    # Step 6: Compose video
    output_path = str(OUTPUT_DIR / "cache_tech_design_brainrot_v2.mp4")
    print(f"\nComposing video -> {output_path}")
    print("(This takes 10-20 minutes...)")

    compose_video(
        text=narration,
        audio_path=audio_path,
        gameplay_clip_path=gameplay_clip,
        output_path=output_path,
        timed_segments=tts_result["timed_segments"],
        word_timings=tts_result["word_timings"],
        diagram_timings=diagram_timings,
    )

    size_mb = Path(output_path).stat().st_size / 1024 / 1024
    print(f"\nVideo generated: {output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
