"""Generate brainrot demo v2 with Stack Overflow humor text."""
import asyncio
import os
import sys

# Run from the project root so get_random_gameplay_clip finds assets/gameplay/
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pipeline.tts_generator import generate_tts
from pipeline.video_composer import compose_video, get_random_gameplay_clip

DEMO_TEXT = (
    "So this guy asks on Stack Overflow how to center a div. "
    "Thirty thousand upvotes. Senior devs are crying. "
    "The CSS working group considered shutting down. "
    "And then some intern says: have you tried display flex? "
    "And that, ladies and gentlemen, is why we drink."
)

OUTPUT_PATH = "/tmp/brainrot_demo_v2.mp4"
AUDIO_PATH = "/tmp/brainrot_demo_v2.mp3"


async def main():
    print("=== Brainrot Demo v2 Video Generator ===\n")

    # Step 1: Generate TTS audio with timing data
    print("[1/3] Generating TTS audio...")
    tts_result = await generate_tts(DEMO_TEXT, AUDIO_PATH)
    audio_path = tts_result["audio_path"]
    timed_segments = tts_result["timed_segments"]
    word_timings = tts_result.get("word_timings")
    print(f"  Audio: {audio_path} ({os.path.getsize(audio_path) / 1024:.1f} KB)")
    print(f"  Segments: {len(timed_segments)} timed caption segments")
    if word_timings:
        print(f"  Word timings: {len(word_timings)} words with real edge-tts timing")

    # Step 2: Pick a random gameplay clip
    print("\n[2/3] Selecting gameplay clip...")
    gameplay_clip = get_random_gameplay_clip()
    if not gameplay_clip:
        print("ERROR: No gameplay clips found in assets/gameplay/")
        sys.exit(1)
    print(f"  Selected: {gameplay_clip}")

    # Step 3: Compose the video with synchronized captions
    print(f"\n[3/3] Compositing video to {OUTPUT_PATH}...")
    compose_video(
        text=DEMO_TEXT,
        audio_path=audio_path,
        gameplay_clip_path=gameplay_clip,
        output_path=OUTPUT_PATH,
        timed_segments=timed_segments,
        word_timings=word_timings,
    )

    # Report result
    file_size = os.path.getsize(OUTPUT_PATH)
    print(f"\n=== Done ===")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Size:   {file_size / 1024:.1f} KB ({file_size / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
