"""Tests for the LLM-powered script transformer."""
import pytest
import httpx

from pipeline.script_transformer import (
    transform_to_brainrot,
    TRANSFORM_PROMPT,
    OLLAMA_URL,
    OLLAMA_MODEL,
)


@pytest.mark.asyncio
async def test_successful_transformation(monkeypatch):
    """transform_to_brainrot returns the LLM response on success."""
    transformed = "so imagine you have this crazy caching system bro"

    async def mock_post(self, url, **kwargs):
        resp = httpx.Response(
            200,
            json={"response": transformed},
            request=httpx.Request("POST", url),
        )
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await transform_to_brainrot("Technical caching design document text")
    assert result == transformed


@pytest.mark.asyncio
async def test_fallback_on_llm_failure(monkeypatch):
    """transform_to_brainrot returns original text when LLM call fails."""
    original = "This is the original technical text."

    async def mock_post(self, url, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await transform_to_brainrot(original)
    assert result == original


@pytest.mark.asyncio
async def test_fallback_on_empty_response(monkeypatch):
    """transform_to_brainrot falls back when LLM returns empty response."""
    original = "Some technical text here."

    async def mock_post(self, url, **kwargs):
        resp = httpx.Response(
            200,
            json={"response": ""},
            request=httpx.Request("POST", url),
        )
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await transform_to_brainrot(original)
    assert result == original


def test_prompt_contains_key_instructions():
    """The transformation prompt includes required style instructions."""
    prompt_lower = TRANSFORM_PROMPT.lower()
    assert "brainrot" in prompt_lower
    assert "no markdown" in prompt_lower
    assert "400 and 600 words" in prompt_lower or "500 words" in prompt_lower
    assert "spoken narration" in prompt_lower
    assert "{text}" in TRANSFORM_PROMPT


def test_prompt_uses_correct_ollama_config():
    """Module constants point to the expected Ollama endpoint and model."""
    assert OLLAMA_URL == "http://localhost:11434/api/generate"
    assert OLLAMA_MODEL == "qwen3:8b"
