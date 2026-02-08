"""LLM-powered script transformation for brainrot narration."""
import os

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = "qwen3:8b"

TRANSFORM_PROMPT = """You are a viral TikTok/Reddit storyteller who makes technical concepts absolutely unhinged and captivating. Rewrite the following text as a spoken narration script for a brainrot-style TikTok video.

Voice and tone:
- Sound like a sleep-deprived engineer on r/ExperiencedDevs having a manic epiphany at 3am
- Hook the viewer HARD in the first sentence — "okay so this is genuinely insane" or "bro I need to talk about this before I lose my mind"
- Build hype like you are revealing a conspiracy — each paragraph should escalate the excitement
- Use natural Gen Z speech: "no cap", "actually cooked", "this goes so hard", "lowkey genius", "rent free in my head", "its giving", "the way this works is actually criminal", "bro what", "okay but like"
- Throw in dramatic pauses: "and then... wait for it..."
- React to your own explanations: "like WHAT", "thats actually insane if you think about it", "I did not just say that out loud"
- Make analogies to everyday things to explain technical concepts
- End with a mind-blown conclusion that makes the viewer feel like they learned something galaxy-brained

Structure:
- Start with a viral hook (first 3 seconds matter)
- Build through 4 to 6 escalating reveals, each one more hype than the last
- Sprinkle in "okay but it gets even crazier" transitions between sections
- End with a satisfying mic-drop conclusion

Hard rules:
- Keep it between 400 and 600 words
- Pure spoken narration only — no markdown, no bullets, no headers, no stage directions
- No emojis, no asterisks, no formatting of any kind
- Every technical concept MUST be explained so a non-engineer could follow
- Output ONLY the narration script text, absolutely nothing else

Text to rewrite:
{text}"""


async def transform_to_brainrot(text: str) -> str:
    """Transform technical text into engaging TikTok brainrot narration.

    Calls a local Ollama LLM to rewrite the input text as casual,
    conversational narration suitable for short-form video.

    Args:
        text: The source text to transform.

    Returns:
        Transformed narration script, or the original text on failure.
    """
    prompt = TRANSFORM_PROMPT.format(text=text)

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json().get("response", "").strip()
            if result:
                return result
    except Exception as e:
        print(f"Script transformation failed ({e}), using original text")

    return text
