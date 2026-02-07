#!/usr/bin/env python3
"""End-to-end test for diagram overlay functionality."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from pipeline import (
    generate_tts,
    compose_video,
    get_random_gameplay_clip,
    generate_diagram_overlays
)

TEMP_DIR = backend_dir / "temp"
OUTPUT_DIR = backend_dir / "output"
GAMEPLAY_DIR = Path(__file__).parent / "assets" / "gameplay"

# Ensure directories exist
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@pytest.mark.asyncio
async def test_diagram_overlays():
    """Test diagram overlay generation end-to-end."""
    print("🧪 Starting end-to-end diagram overlay test...")

    # Read test input
    test_input_path = Path(__file__).parent / "test_inputs" / "architecture_test.txt"
    with open(test_input_path, 'r') as f:
        text = f.read()

    print(f"✅ Loaded test input ({len(text)} chars)")
    print(f"   Contains Mermaid block: {'```mermaid' in text}")

    # Generate TTS with word timings
    print("\n🎙️  Generating TTS audio with word timings...")
    audio_path = str(TEMP_DIR / "test_e2e.mp3")
    tts_result = await generate_tts(text, audio_path)

    # Calculate duration from word timings
    duration = 0.0
    if tts_result['word_timings']:
        last_word = tts_result['word_timings'][-1]
        duration = last_word['end_ms'] / 1000.0

    print(f"✅ TTS generated: {duration:.2f}s")
    print(f"   Word timings: {len(tts_result['word_timings'])} words")

    # Generate diagram overlays
    print("\n📊 Generating diagram overlays...")
    diagram_timings = await generate_diagram_overlays(
        text,
        tts_result["word_timings"],
        TEMP_DIR
    )

    print(f"✅ Diagram overlays generated: {len(diagram_timings)} diagrams")
    for i, diagram in enumerate(diagram_timings):
        print(f"   Diagram {i+1}: {diagram['label']} at {diagram['start_s']:.2f}s for {diagram['duration_s']:.2f}s")
        print(f"   PNG path: {diagram['png_path']}")
        # Verify PNG exists
        if Path(diagram['png_path']).exists():
            print(f"   ✅ PNG file exists")
        else:
            print(f"   ❌ PNG file missing!")

    # Select gameplay clip
    print("\n🎮 Selecting gameplay clip...")
    gameplay_clip = get_random_gameplay_clip(str(GAMEPLAY_DIR))
    print(f"✅ Gameplay clip: {gameplay_clip}")

    # Compose video
    print("\n🎬 Composing video with diagrams and captions...")
    output_path = str(OUTPUT_DIR / "test_e2e_diagrams.mp4")

    compose_video(
        text=text,
        audio_path=audio_path,
        gameplay_clip_path=gameplay_clip,
        output_path=output_path,
        timed_segments=tts_result["timed_segments"],
        word_timings=tts_result["word_timings"],
        diagram_timings=diagram_timings
    )

    print(f"\n✅ Video generated successfully!")
    print(f"   Output: {output_path}")

    # Verify output exists
    if Path(output_path).exists():
        size_mb = Path(output_path).stat().st_size / 1024 / 1024
        print(f"   File size: {size_mb:.2f} MB")
        print(f"\n🎉 END-TO-END TEST PASSED!")
        print(f"\nTo view the video:")
        print(f"   open {output_path}")
        return True
    else:
        print(f"\n❌ Output video not found!")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_diagram_overlays())
    sys.exit(0 if success else 1)
