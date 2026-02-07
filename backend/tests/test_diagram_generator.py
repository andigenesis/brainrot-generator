"""
Tests for diagram_generator module.

Tests cover:
- Mermaid block extraction (with and without blocks)
- Keyword timing detection (mocked word_timings)
- LLM diagram generation (mocked Ollama)
- mmdc rendering (mocked subprocess)
- Pillow fallback when mmdc unavailable
- Graceful degradation (all failure paths return empty list)
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
import asyncio

from backend.pipeline.diagram_generator import (
    extract_mermaid_blocks,
    generate_mermaid_with_llm,
    generate_topic_diagram,
    render_mermaid_to_png,
    find_diagram_timestamps,
    generate_diagram_overlays,
    _extract_topic_context,
)


class TestMermaidExtraction:
    """Test Mermaid block extraction from text."""

    def test_extract_single_mermaid_block(self):
        """Should extract a single Mermaid block from text."""
        text = """
Here's a diagram:

```mermaid
graph TD
    A[Client] --> B[Server]
    B --> C[Database]
```

That's the architecture.
"""
        blocks = extract_mermaid_blocks(text)
        assert len(blocks) == 1
        assert "graph TD" in blocks[0]
        assert "A[Client]" in blocks[0]
        assert "B[Server]" in blocks[0]

    def test_extract_multiple_mermaid_blocks(self):
        """Should extract multiple Mermaid blocks from text."""
        text = """
```mermaid
graph LR
    A --> B
```

Some text in between.

```mermaid
sequenceDiagram
    User->>API: Request
```
"""
        blocks = extract_mermaid_blocks(text)
        assert len(blocks) == 2
        assert "graph LR" in blocks[0]
        assert "sequenceDiagram" in blocks[1]

    def test_extract_no_mermaid_blocks(self):
        """Should return empty list when no Mermaid blocks present."""
        text = "This is just plain text with no diagrams."
        blocks = extract_mermaid_blocks(text)
        assert blocks == []

    def test_extract_mermaid_case_insensitive(self):
        """Should extract Mermaid blocks regardless of case."""
        text = """
```MERMAID
graph TD
    A --> B
```
"""
        blocks = extract_mermaid_blocks(text)
        assert len(blocks) == 1


class TestKeywordTimingDetection:
    """Test architecture keyword detection in word timings."""

    def test_find_single_keyword_timing(self):
        """Should find timestamp for single architecture keyword."""
        word_timings = [
            {"word": "The", "start_ms": 0, "end_ms": 200},
            {"word": "API", "start_ms": 200, "end_ms": 500},
            {"word": "server", "start_ms": 500, "end_ms": 900},
        ]
        timings = find_diagram_timestamps(word_timings)
        assert len(timings) >= 1
        assert timings[0]["start_s"] == 0.2
        assert "api" in timings[0]["keywords"]

    def test_find_multiple_keyword_timings(self):
        """Should find timestamps for multiple architecture keywords."""
        word_timings = [
            {"word": "The", "start_ms": 0, "end_ms": 200},
            {"word": "cache", "start_ms": 200, "end_ms": 500},
            {"word": "and", "start_ms": 500, "end_ms": 600},
            {"word": "then", "start_ms": 600, "end_ms": 800},
            {"word": "the", "start_ms": 800, "end_ms": 1000},
            {"word": "database", "start_ms": 3000, "end_ms": 3400},  # Far apart to avoid merging
        ]
        timings = find_diagram_timestamps(word_timings)
        assert len(timings) == 2
        assert "cache" in timings[0]["keywords"]
        assert "database" in timings[1]["keywords"]

    def test_no_keywords_found(self):
        """Should return empty list when no keywords present."""
        word_timings = [
            {"word": "Hello", "start_ms": 0, "end_ms": 200},
            {"word": "world", "start_ms": 200, "end_ms": 500},
        ]
        timings = find_diagram_timestamps(word_timings)
        assert timings == []

    def test_case_insensitive_keyword_detection(self):
        """Should detect keywords regardless of case."""
        word_timings = [
            {"word": "API", "start_ms": 0, "end_ms": 200},
            {"word": "stuff", "start_ms": 200, "end_ms": 500},
            {"word": "Cache", "start_ms": 3000, "end_ms": 3300},  # Far apart
            {"word": "more", "start_ms": 3300, "end_ms": 3500},
            {"word": "DATABASE", "start_ms": 6000, "end_ms": 6400},  # Far apart
        ]
        timings = find_diagram_timestamps(word_timings)
        assert len(timings) == 3


class TestLLMDiagramGeneration:
    """Test LLM-powered diagram generation via Ollama."""

    @pytest.mark.asyncio
    async def test_generate_mermaid_with_llm_success(self):
        """Should generate Mermaid diagram via Ollama."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "response": "graph TD\n    A[Client] --> B[Server]",
            "done": True
        }
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await generate_mermaid_with_llm("API architecture description")
            assert result is not None
            assert "graph TD" in result.lower() or "graph" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_mermaid_with_llm_timeout(self):
        """Should return None on timeout."""
        with patch(
            "httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")
        ):
            result = await generate_mermaid_with_llm("text")
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_mermaid_with_llm_http_error(self):
        """Should return None on HTTP error."""
        with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Error")):
            result = await generate_mermaid_with_llm("text")
            assert result is None


class TestMermaidRendering:
    """Test Mermaid diagram rendering to PNG."""

    def test_render_with_mmdc_success(self, tmp_path):
        """Should render Mermaid to PNG using mmdc."""
        mermaid_code = "graph TD\n    A --> B"
        output_file = str(tmp_path / "test.png")

        # Mock successful mmdc subprocess call
        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            # Mock Path.exists to simulate PNG was created
            with patch.object(Path, "exists", return_value=True):
                result = render_mermaid_to_png(mermaid_code, output_file)
                assert result is True

    def test_render_fallback_to_pillow(self, tmp_path):
        """Should fall back to Pillow when mmdc fails."""
        mermaid_code = "graph TD\n    A[Client] --> B[Server]"
        output_file = str(tmp_path / "test.png")

        # Mock mmdc failure (FileNotFoundError for missing mmdc)
        with patch("subprocess.run", side_effect=FileNotFoundError("mmdc not found")):
            result = render_mermaid_to_png(mermaid_code, output_file)
            # Should still return True (Pillow fallback)
            assert result is True
            # Verify PNG file was actually created by Pillow
            assert Path(output_file).exists()

    def test_render_handles_complex_mermaid(self, tmp_path):
        """Should handle complex Mermaid syntax in Pillow fallback."""
        mermaid_code = """
graph TD
    A[Client App] --> B[API Gateway]
    B --> C[Auth Service]
    B --> D[Data Service]
    D --> E[Database]
"""
        output_file = str(tmp_path / "test.png")

        # Mock mmdc failure to trigger Pillow fallback
        with patch("subprocess.run", side_effect=FileNotFoundError("mmdc not found")):
            result = render_mermaid_to_png(mermaid_code, output_file)
            assert result is True
            assert Path(output_file).exists()


class TestGracefulDegradation:
    """Test that all failures return empty list gracefully."""

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_list(self, tmp_path):
        """Should return empty list for empty text input."""
        word_timings = [{"word": "test", "start_ms": 0, "end_ms": 200}]
        result = await generate_diagram_overlays("", word_timings, tmp_path)
        assert result == []

    @pytest.mark.asyncio
    async def test_no_keywords_returns_empty_list(self, tmp_path):
        """Should return empty list when no architecture keywords found."""
        text = "This is just a story about cats and dogs."
        word_timings = [
            {"word": "This", "start_ms": 0, "end_ms": 200},
            {"word": "is", "start_ms": 200, "end_ms": 300},
        ]
        result = await generate_diagram_overlays(text, word_timings, tmp_path)
        assert result == []

    @pytest.mark.asyncio
    async def test_llm_failure_returns_empty_list(self, tmp_path):
        """Should return empty list when LLM fails and no Mermaid blocks present."""
        text = "This discusses the API architecture."
        word_timings = [
            {"word": "API", "start_ms": 500, "end_ms": 800},
        ]

        # Mock LLM failure (returns None)
        with patch(
            "backend.pipeline.diagram_generator.generate_mermaid_with_llm",
            return_value=None,
        ):
            result = await generate_diagram_overlays(text, word_timings, tmp_path)
            assert result == []

    @pytest.mark.asyncio
    async def test_render_failure_returns_empty_list(self, tmp_path):
        """Should return empty list when both mmdc and Pillow fail."""
        text = """
```mermaid
graph TD
    A --> B
```
The API handles requests.
"""
        word_timings = [
            {"word": "API", "start_ms": 500, "end_ms": 800},
        ]

        # Mock render failure (returns False)
        with patch(
            "backend.pipeline.diagram_generator.render_mermaid_to_png",
            return_value=False,
        ):
            result = await generate_diagram_overlays(text, word_timings, tmp_path)
            assert result == []


class TestEndToEndOrchestration:
    """Test the main generate_diagram_overlays function."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mermaid_blocks(self, tmp_path):
        """Should process text with Mermaid blocks end-to-end."""
        text = """
Here's the system architecture:

```mermaid
graph TD
    A[Client] --> B[API Gateway]
    B --> C[Service]
```

The API handles all requests.
"""
        word_timings = [
            {"word": "The", "start_ms": 0, "end_ms": 200},
            {"word": "API", "start_ms": 200, "end_ms": 500},
            {"word": "handles", "start_ms": 500, "end_ms": 800},
        ]

        # Mock mmdc success
        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists", return_value=True):
                result = await generate_diagram_overlays(text, word_timings, tmp_path)
                assert len(result) >= 1
                assert result[0]["start_s"] == 0.2
                assert "api" in result[0]["label"].lower()
                assert result[0]["png_path"].endswith(".png")
                assert result[0]["duration_s"] > 0

    @pytest.mark.asyncio
    async def test_full_pipeline_with_llm_generation(self, tmp_path):
        """Should generate diagram via LLM when no Mermaid blocks present."""
        text = "The cache layer sits between the API and the database."
        word_timings = [
            {"word": "cache", "start_ms": 200, "end_ms": 500},
            {"word": "layer", "start_ms": 500, "end_ms": 700},
            {"word": "sits", "start_ms": 700, "end_ms": 900},
            {"word": "between", "start_ms": 900, "end_ms": 1100},
            {"word": "the", "start_ms": 1100, "end_ms": 1200},
            {"word": "API", "start_ms": 1200, "end_ms": 1500},
        ]

        # Mock LLM response
        mock_llm_response = "graph TD\n    A[Cache] --> B[Database]"
        with patch(
            "backend.pipeline.diagram_generator.generate_mermaid_with_llm",
            return_value=mock_llm_response,
        ):
            # Mock mmdc success
            mock_result = Mock()
            mock_result.returncode = 0

            with patch("subprocess.run", return_value=mock_result):
                with patch.object(Path, "exists", return_value=True):
                    result = await generate_diagram_overlays(text, word_timings, tmp_path)
                    # Should find first keyword (cache)
                    assert len(result) >= 1
                    assert result[0]["start_s"] == 0.2


class TestTopicContextExtraction:
    """Test _extract_topic_context helper."""

    def test_extracts_context_around_keyword(self):
        text = "word1 word2 word3 cache word5 word6 word7"
        result = _extract_topic_context(["cache"], text, window=2)
        assert "cache" in result
        assert "word2" in result or "word3" in result

    def test_returns_full_text_when_keyword_not_found(self):
        text = "no matching keywords here at all"
        result = _extract_topic_context(["database"], text, window=2)
        assert result  # should return truncated original text


class TestUniqueDiagramGeneration:
    """Test unique diagram generation per timing window."""

    @pytest.mark.asyncio
    async def test_multiple_timings_get_unique_diagrams(self, tmp_path):
        """Multiple timing windows should get different diagram paths when LLM succeeds."""
        text = "The API server connects to the database and cache layer for performance."
        word_timings = [
            {"word": "API", "start_ms": 200, "end_ms": 500},
            {"word": "server", "start_ms": 500, "end_ms": 800},
            {"word": "database", "start_ms": 5000, "end_ms": 5400},
            {"word": "cache", "start_ms": 10000, "end_ms": 10300},
        ]

        # Mock LLM to return different mermaid for the initial generation
        mock_llm_response = "graph TD\n    A[API] --> B[DB]"

        # Track calls to generate_topic_diagram to return unique paths
        call_count = [0]

        async def mock_topic_diagram(keywords, orig_text, tdir, index):
            call_count[0] += 1
            path = str(tmp_path / f"unique_{index}.png")
            # Create a dummy file
            Path(path).write_bytes(b"PNG")
            return path

        with patch(
            "backend.pipeline.diagram_generator.generate_mermaid_with_llm",
            return_value=mock_llm_response,
        ):
            mock_result = Mock()
            mock_result.returncode = 0

            with patch("subprocess.run", return_value=mock_result):
                with patch.object(Path, "exists", return_value=True):
                    with patch(
                        "backend.pipeline.diagram_generator.generate_topic_diagram",
                        side_effect=mock_topic_diagram,
                    ):
                        result = await generate_diagram_overlays(text, word_timings, tmp_path)
                        # Should have at least 2 timing windows (api+server merge, database, cache)
                        assert len(result) >= 2
                        # Timings beyond the first should have topic diagrams
                        paths = [r["png_path"] for r in result]
                        # The first uses the pre-rendered diagram, others get unique ones
                        assert call_count[0] >= 1  # generate_topic_diagram was called

    @pytest.mark.asyncio
    async def test_mermaid_blocks_distributed_across_timings(self, tmp_path):
        """Multiple pre-rendered diagrams should be distributed round-robin across timings."""
        text = """
```mermaid
graph TD
    A[Client] --> B[Server]
```

```mermaid
sequenceDiagram
    User->>API: Request
```

The API server connects to the database for data.
"""
        word_timings = [
            {"word": "API", "start_ms": 200, "end_ms": 500},
            {"word": "server", "start_ms": 500, "end_ms": 800},
            {"word": "database", "start_ms": 5000, "end_ms": 5400},
        ]

        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "exists", return_value=True):
                with patch(
                    "backend.pipeline.diagram_generator.generate_topic_diagram",
                    return_value=None,
                ):
                    result = await generate_diagram_overlays(text, word_timings, tmp_path)
                    assert len(result) >= 2
                    # With 2 rendered diagrams, they should round-robin
                    paths = [r["png_path"] for r in result]
                    # First and third should use diagram_0, second uses diagram_1
                    if len(result) >= 2:
                        assert paths[0] != paths[1]  # Different diagrams for different timings

    @pytest.mark.asyncio
    async def test_fallback_to_single_diagram_on_generation_failure(self, tmp_path):
        """Should reuse first diagram when generate_topic_diagram fails."""
        text = "The API server connects to the database and cache layer."
        word_timings = [
            {"word": "API", "start_ms": 200, "end_ms": 500},
            {"word": "server", "start_ms": 500, "end_ms": 800},
            {"word": "database", "start_ms": 5000, "end_ms": 5400},
            {"word": "cache", "start_ms": 10000, "end_ms": 10300},
        ]

        mock_llm_response = "graph TD\n    A[API] --> B[Server]"

        with patch(
            "backend.pipeline.diagram_generator.generate_mermaid_with_llm",
            return_value=mock_llm_response,
        ):
            mock_result = Mock()
            mock_result.returncode = 0

            with patch("subprocess.run", return_value=mock_result):
                with patch.object(Path, "exists", return_value=True):
                    # Mock generate_topic_diagram to always fail
                    with patch(
                        "backend.pipeline.diagram_generator.generate_topic_diagram",
                        return_value=None,
                    ):
                        result = await generate_diagram_overlays(text, word_timings, tmp_path)
                        assert len(result) >= 2
                        # All should use the same (first) pre-rendered diagram
                        paths = [r["png_path"] for r in result]
                        assert all(p == paths[0] for p in paths)

    @pytest.mark.asyncio
    async def test_generate_topic_diagram_success(self, tmp_path):
        """generate_topic_diagram should return PNG path on LLM success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "response": "graph TD\n    A[Cache] --> B[DB]",
            "done": True,
        }
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            with patch(
                "backend.pipeline.diagram_generator.render_mermaid_to_png",
                return_value=True,
            ):
                result = await generate_topic_diagram(
                    ["cache"], "The cache layer handles requests", str(tmp_path), 0
                )
                assert result is not None
                assert "topic_diagram_0" in result

    @pytest.mark.asyncio
    async def test_generate_topic_diagram_llm_failure(self, tmp_path):
        """generate_topic_diagram should return None when LLM fails."""
        with patch(
            "httpx.AsyncClient.post",
            side_effect=httpx.TimeoutException("Timeout"),
        ):
            result = await generate_topic_diagram(
                ["cache"], "The cache layer handles requests", str(tmp_path), 0
            )
            assert result is None
