#!/usr/bin/env python3
"""Test synchronized captions functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.tts_generator import generate_tts
from pipeline.video_composer import compose_video, get_random_gameplay_clip

async def test_synchronized_captions():
    """Generate a test video with synchronized captions."""
    print("🎬 Testing synchronized captions...\n")

    # Short test text
    test_text = "This is a test of synchronized captions. Each sentence should appear separately. The timing should match the voice narration."

    print(f"📝 Test text: {test_text}\n")

    # Step 1: Generate TTS with timing data
    print("🎙️  Step 1: Generating TTS with timing data...")
    audio_output_path = "/tmp/test_tts_output.mp3"
    tts_result = await generate_tts(test_text, audio_output_path, voice="en-US-AriaNeural")

    audio_path = tts_result["audio_path"]
    timed_segments = tts_result["timed_segments"]
    word_timings = tts_result.get("word_timings")

    print(f"   ✓ Audio generated: {audio_path}")
    print(f"   ✓ Found {len(timed_segments)} timed segments:")
    if word_timings:
        print(f"   ✓ Got {len(word_timings)} real per-word timings from edge-tts")

    for i, seg in enumerate(timed_segments, 1):
        print(f"      {i}. \"{seg['text']}\" ({seg['start_ms']}ms - {seg['end_ms']}ms)")

    # Step 2: Get random gameplay clip
    print("\n🎮 Step 2: Selecting gameplay clip...")
    gameplay_clip_path = get_random_gameplay_clip()
    if not gameplay_clip_path:
        print("   ⚠️  No gameplay clips found, using first available clip")
        gameplay_clip_path = "/opt/andi/projects/brainrot-generator/assets/gameplay/minecraft_parkour_01.mp4"
    print(f"   ✓ Selected: {gameplay_clip_path}")

    # Step 3: Compose video with synchronized captions
    print("\n🎥 Step 3: Composing video with synchronized captions...")
    output_path = "/tmp/test_synchronized_captions.mp4"

    compose_video(
        text="",  # Not used when timed_segments is provided
        audio_path=audio_path,
        gameplay_clip_path=gameplay_clip_path,
        output_path=output_path,
        timed_segments=timed_segments,
        word_timings=word_timings,
    )

    print(f"   ✓ Video generated: {output_path}")

    # Check file size
    file_size = os.path.getsize(output_path)
    file_size_kb = file_size / 1024

    print(f"\n✅ Test complete!")
    print(f"   Output: {output_path}")
    print(f"   Size: {file_size_kb:.1f} KB")
    print(f"   Segments: {len(timed_segments)}")

    if file_size > 0:
        print("\n🎉 Synchronized captions test PASSED!")
        print(f"\nTo view the test video, run:")
        print(f"   open {output_path}")
        return True
    else:
        print("\n❌ Test FAILED: Output file is empty")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_synchronized_captions())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
