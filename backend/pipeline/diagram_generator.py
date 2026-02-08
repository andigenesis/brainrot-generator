"""Architecture diagram extraction, generation, and overlay timing for brainrot videos."""
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image, ImageDraw, ImageFont


# Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = "qwen3:8b"

# Architecture keywords to detect diagram timing
ARCHITECTURE_KEYWORDS = {
    "cache", "caching", "cached",
    "api", "endpoint", "rest",
    "database", "db", "sql", "query",
    "service", "microservice",
    "server", "client",
    "layer", "architecture",
    "pipeline", "workflow",
    "queue", "message", "broker",
    "storage", "bucket",
    "authentication", "auth",
    "load balancer", "proxy",
    "container", "docker", "kubernetes",
}

# Mermaid diagram generation prompt
DIAGRAM_PROMPT = """Generate a Mermaid diagram that visualizes the architecture or workflow described in the following text.

Rules:
- Output ONLY the Mermaid code, starting with the diagram type (graph, sequenceDiagram, classDiagram, etc.)
- Do NOT include triple backticks or any markdown formatting
- Keep it simple and focused on the main architecture components mentioned
- Use clear, short labels for nodes
- If the text describes a sequence of operations, use sequenceDiagram
- If the text describes system architecture, use graph TD (top-down flowchart)
- If the text describes data flow, use graph LR (left-right flowchart)
- Maximum 8 nodes for clarity

Text to visualize:
{text}"""

# Topic-specific diagram prompt for unique diagrams per timing window
TOPIC_DIAGRAM_PROMPT = """Generate a Mermaid diagram focused specifically on the following concepts: {keywords}

Context from the narration:
{topic_context}

Rules:
- Output ONLY the Mermaid code, starting with the diagram type (graph, sequenceDiagram, classDiagram, etc.)
- Do NOT include triple backticks or any markdown formatting
- Create a DIFFERENT diagram from any previous ones - focus on the relationships and details specific to these concepts
- Use clear, short labels for nodes
- Maximum 8 nodes for clarity
- Choose the most appropriate diagram type for these specific concepts"""


def _extract_topic_context(keywords: list[str], original_text: str, window: int = 50) -> str:
    """Extract text surrounding keywords from the original narration.

    Args:
        keywords: Keywords to search for in text
        original_text: Full narration text
        window: Number of words before/after keyword to include

    Returns:
        Extracted context string
    """
    words = original_text.split()
    if not words:
        return original_text

    contexts = []
    for keyword in keywords:
        for i, word in enumerate(words):
            if keyword.lower() in word.lower():
                start = max(0, i - window)
                end = min(len(words), i + window + 1)
                contexts.append(' '.join(words[start:end]))
                break

    return ' '.join(contexts) if contexts else original_text[:500]


async def generate_topic_diagram(
    keywords: list[str],
    original_text: str,
    temp_dir: str,
    index: int,
) -> Optional[str]:
    """Generate a unique diagram for a specific topic/timing window.

    Extracts context around the keywords from the narration, generates a
    focused Mermaid diagram via LLM, and renders it to PNG.

    Args:
        keywords: Keywords for this timing window
        original_text: Full narration text for context extraction
        temp_dir: Directory for temporary PNG files
        index: Index for unique filename

    Returns:
        Path to rendered PNG, or None on failure
    """
    topic_context = _extract_topic_context(keywords, original_text)
    prompt = TOPIC_DIAGRAM_PROMPT.format(
        keywords=', '.join(keywords),
        topic_context=topic_context,
    )

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
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

            if result and any(kw in result.lower() for kw in ["graph", "sequencediagram", "classdiagram", "flowchart"]):
                output_path = os.path.join(temp_dir, f"topic_diagram_{index}.png")
                if render_mermaid_to_png(result, output_path):
                    return output_path
    except Exception as e:
        print(f"Topic diagram generation failed for keywords {keywords} ({e})")

    return None


def extract_mermaid_blocks(text: str) -> list[str]:
    """Extract Mermaid diagram code blocks from markdown-formatted text.

    Looks for triple-backtick code blocks with 'mermaid' language identifier.

    Args:
        text: Input text that may contain Mermaid code blocks

    Returns:
        List of Mermaid diagram code strings (without the backticks)
    """
    # Pattern: ```mermaid\n...\n```
    pattern = r'```mermaid\s*\n(.*?)\n```'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    return [m.strip() for m in matches if m.strip()]


async def generate_mermaid_with_llm(text: str) -> Optional[str]:
    """Generate a Mermaid diagram from text using Ollama LLM.

    Calls local Ollama instance to create an architecture diagram based on
    the input text content.

    Args:
        text: Source text describing architecture or workflow

    Returns:
        Mermaid diagram code string, or None on failure
    """
    prompt = DIAGRAM_PROMPT.format(text=text)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
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

            # Validate that we got something that looks like Mermaid
            if result and any(kw in result.lower() for kw in ["graph", "sequencediagram", "classdiagram", "flowchart"]):
                return result
    except Exception as e:
        print(f"LLM diagram generation failed ({e})")

    return None


def _render_simple_diagram_pillow(mermaid_code: str, output_path: str) -> bool:
    """Fallback renderer: create simple box-and-arrow diagram using Pillow.

    Parses basic Mermaid graph syntax and renders boxes with connecting lines.
    This is a simplified fallback when mmdc is not available.

    Args:
        mermaid_code: Mermaid diagram code
        output_path: Where to save the PNG file

    Returns:
        True if rendering succeeded, False otherwise
    """
    try:
        # Parse simple graph structure: A --> B, A[Label]
        # This is a very basic parser for demonstration
        nodes = {}
        edges = []

        for line in mermaid_code.split('\n'):
            line = line.strip()

            # Skip diagram type declarations and empty lines
            if not line or line.startswith('graph') or line.startswith('flowchart'):
                continue

            # Parse edge: A --> B or A[Label] --> B[Label2]
            if '-->' in line:
                parts = line.split('-->')
                if len(parts) == 2:
                    source = parts[0].strip().split('[')[0].strip()
                    target = parts[1].strip().split('[')[0].strip()
                    edges.append((source, target))

                    # Extract labels if present
                    for part in parts:
                        if '[' in part and ']' in part:
                            node_id = part.split('[')[0].strip()
                            label = part.split('[')[1].split(']')[0].strip()
                            nodes[node_id] = label
                        else:
                            node_id = part.strip()
                            if node_id and node_id not in nodes:
                                nodes[node_id] = node_id

        if not nodes:
            return False

        # Create image (1080x1920 for vertical video, but we'll use center portion)
        img_width = 1080
        img_height = 800
        img = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Load font
        try:
            font = ImageFont.truetype('/opt/andi/projects/brainrot-generator/assets/fonts/Montserrat-Bold.ttf', 24)
            title_font = ImageFont.truetype('/opt/andi/projects/brainrot-generator/assets/fonts/Montserrat-Bold.ttf', 32)
        except OSError:
            font = ImageFont.load_default()
            title_font = font

        # Layout nodes in a simple top-to-bottom flow
        node_positions = {}
        box_width = 200
        box_height = 60
        spacing_y = 120
        start_y = 100

        node_list = list(nodes.keys())
        for i, node_id in enumerate(node_list):
            x = img_width // 2
            y = start_y + (i * spacing_y)
            node_positions[node_id] = (x, y)

        # Draw edges (arrows)
        for source, target in edges:
            if source in node_positions and target in node_positions:
                x1, y1 = node_positions[source]
                x2, y2 = node_positions[target]

                # Draw line from bottom of source to top of target
                draw.line(
                    [(x1, y1 + box_height//2), (x2, y2 - box_height//2)],
                    fill=(100, 100, 100),
                    width=3
                )

                # Draw arrowhead
                arrow_size = 10
                draw.polygon(
                    [
                        (x2, y2 - box_height//2),
                        (x2 - arrow_size, y2 - box_height//2 - arrow_size),
                        (x2 + arrow_size, y2 - box_height//2 - arrow_size),
                    ],
                    fill=(100, 100, 100)
                )

        # Draw nodes (boxes with text)
        for node_id, label in nodes.items():
            if node_id in node_positions:
                x, y = node_positions[node_id]

                # Draw box
                draw.rectangle(
                    [
                        x - box_width//2,
                        y - box_height//2,
                        x + box_width//2,
                        y + box_height//2
                    ],
                    fill=(200, 230, 255),
                    outline=(50, 100, 200),
                    width=3
                )

                # Draw text (centered)
                bbox = draw.textbbox((0, 0), label, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                draw.text(
                    (x - text_width//2, y - text_height//2),
                    label,
                    fill=(0, 0, 0),
                    font=font
                )

        # Add title
        draw.text(
            (40, 30),
            "Architecture Diagram",
            fill=(50, 50, 50),
            font=title_font
        )

        # Save
        img.save(output_path, 'PNG')
        return True

    except Exception as e:
        print(f"Pillow diagram rendering failed ({e})")
        return False


def render_mermaid_to_png(mermaid_code: str, output_path: str) -> bool:
    """Render Mermaid diagram code to PNG image.

    Tries mmdc (Mermaid CLI) first, falls back to Pillow for simple diagrams.

    Args:
        mermaid_code: Mermaid diagram code
        output_path: Where to save the PNG file

    Returns:
        True if rendering succeeded, False otherwise
    """
    # Try mmdc first (Mermaid CLI)
    try:
        # Write mermaid code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
            f.write(mermaid_code)
            mmd_path = f.name

        # Run mmdc
        result = subprocess.run(
            ['mmdc', '-i', mmd_path, '-o', output_path, '-b', 'transparent'],
            capture_output=True,
            timeout=30
        )

        # Cleanup temp file
        Path(mmd_path).unlink(missing_ok=True)

        if result.returncode == 0 and Path(output_path).exists():
            return True

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"mmdc rendering failed ({e}), trying Pillow fallback")

    # Fallback to Pillow
    return _render_simple_diagram_pillow(mermaid_code, output_path)


def find_diagram_timestamps(word_timings: list[dict], min_duration_s: float = 3.0) -> list[dict]:
    """Find timestamps where architecture keywords appear in narration.

    Scans word timing data for architecture-related keywords and determines
    when to display diagram overlays.

    Args:
        word_timings: List of {word, start_ms, end_ms} dicts from TTS
        min_duration_s: Minimum display duration in seconds

    Returns:
        List of {start_s, duration_s, keywords} timing objects
    """
    diagram_timings = []

    for i, wt in enumerate(word_timings):
        word_lower = wt["word"].lower().strip('.,!?;:')

        if word_lower in ARCHITECTURE_KEYWORDS:
            start_s = wt["start_ms"] / 1000.0

            # Check if we can extend to include nearby context (next few words)
            end_ms = wt["end_ms"]
            keywords_found = [word_lower]

            # Look ahead for more keywords in next 5 words
            for j in range(i + 1, min(i + 6, len(word_timings))):
                next_word = word_timings[j]["word"].lower().strip('.,!?;:')
                if next_word in ARCHITECTURE_KEYWORDS:
                    keywords_found.append(next_word)
                    end_ms = word_timings[j]["end_ms"]

            end_s = end_ms / 1000.0
            duration_s = max(end_s - start_s, min_duration_s)

            # Avoid duplicates (if previous timing overlaps)
            if diagram_timings and abs(diagram_timings[-1]["start_s"] - start_s) < 2.0:
                # Extend previous timing instead of creating new one
                diagram_timings[-1]["duration_s"] = max(
                    diagram_timings[-1]["duration_s"],
                    (end_s - diagram_timings[-1]["start_s"])
                )
                diagram_timings[-1]["keywords"].extend(keywords_found)
            else:
                diagram_timings.append({
                    "start_s": start_s,
                    "duration_s": duration_s,
                    "keywords": keywords_found
                })

    return diagram_timings


async def generate_diagram_overlays(
    text: str,
    word_timings: list[dict],
    temp_dir: Path
) -> list[dict]:
    """Main orchestration function for diagram generation pipeline.

    Steps:
    1. Extract existing Mermaid blocks from text
    2. If none found, generate diagram with LLM
    3. Render diagram(s) to PNG
    4. Find timestamps for diagram display based on keywords
    5. Return timing + path info for video composition

    Gracefully degrades: returns empty list on any failure.

    Args:
        text: Input text (may contain Mermaid blocks)
        word_timings: Word timing data from TTS
        temp_dir: Directory for temporary PNG files

    Returns:
        List of {png_path, start_s, duration_s, label} dicts
    """
    diagram_overlays = []

    try:
        # Step 1: Extract Mermaid blocks
        mermaid_blocks = extract_mermaid_blocks(text)

        # Step 2: Generate with LLM if none found
        if not mermaid_blocks:
            llm_mermaid = await generate_mermaid_with_llm(text)
            if llm_mermaid:
                mermaid_blocks = [llm_mermaid]

        if not mermaid_blocks:
            print("No diagrams found or generated, skipping diagram overlays")
            return []

        # Step 3: Render diagrams to PNG
        rendered_diagrams = []
        for i, mermaid_code in enumerate(mermaid_blocks):
            output_path = temp_dir / f"diagram_{i}.png"
            if render_mermaid_to_png(mermaid_code, str(output_path)):
                rendered_diagrams.append(str(output_path))
            else:
                print(f"Failed to render diagram {i}, skipping")

        if not rendered_diagrams:
            print("No diagrams successfully rendered")
            return []

        # Step 4: Find timestamps
        diagram_timings = find_diagram_timestamps(word_timings)

        if not diagram_timings:
            print("No architecture keywords found in narration, skipping diagram overlays")
            return []

        # Step 5: Map diagrams to timings with unique diagrams per window
        # Cap at 4 diagram overlays to prevent OOM during video compositing
        diagram_timings = diagram_timings[:4]
        for i, timing in enumerate(diagram_timings):
            png_path = None

            # First: distribute pre-rendered diagrams round-robin
            if rendered_diagrams:
                png_path = rendered_diagrams[i % len(rendered_diagrams)]

            # If we have fewer pre-rendered diagrams than timings and this
            # index exceeds what we have, try generating a topic-specific one
            if i >= len(rendered_diagrams):
                topic_path = await generate_topic_diagram(
                    timing["keywords"], text, str(temp_dir), i
                )
                if topic_path:
                    png_path = topic_path

            # Final fallback: reuse first rendered diagram
            if not png_path:
                png_path = rendered_diagrams[0]

            diagram_overlays.append({
                "png_path": png_path,
                "start_s": timing["start_s"],
                "duration_s": timing["duration_s"],
                "label": f"Architecture: {', '.join(timing['keywords'][:2])}"
            })

        print(f"Generated {len(diagram_overlays)} diagram overlay(s)")

    except Exception as e:
        print(f"Diagram generation pipeline failed ({e}), returning empty list")

    return diagram_overlays
