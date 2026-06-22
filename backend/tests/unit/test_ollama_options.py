from __future__ import annotations

import json

import httpx
import respx

from backend.services.ollama_client import (
    DEFAULT_KEEP_ALIVE,
    DEFAULT_NUM_THREAD,
    Operation,
    OllamaClient,
    build_options,
)

_BASE = "http://localhost:11434"


# ---------- build_options ----------

def test_default_options_have_ctx_thread() -> None:
    opts = build_options(Operation.DEFAULT)
    assert opts["num_ctx"] == 4096
    assert opts["num_thread"] == DEFAULT_NUM_THREAD
    assert opts["temperature"] == 0.3


def test_cover_letter_caps_at_4096() -> None:
    # Large prompt: cover letter caps context at 4096 (swap-cliff guard).
    opts = build_options(Operation.COVER_LETTER, prompt_tokens=9000, max_tokens=512)
    assert opts["num_ctx"] == 4096


def test_small_prompt_downscales_to_2048() -> None:
    # The down-scale path: a short retrieval should not reserve 4096 of KV cache.
    opts = build_options(Operation.CHAT, prompt_tokens=200, max_tokens=256)
    assert opts["num_ctx"] == 2048


def test_num_predict_threaded_when_set() -> None:
    opts = build_options(Operation.DEFAULT, max_tokens=128)
    assert opts["num_predict"] == 128


# ---------- generate payload ----------

@respx.mock
def test_generate_payload_includes_calibrated_options() -> None:
    route = respx.post(f"{_BASE}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "hi"})
    )
    OllamaClient(base_url=_BASE).generate(model="qwen3:8b", prompt="p")
    sent = json.loads(route.calls.last.request.content)
    assert sent["options"]["num_ctx"] == 4096
    assert sent["options"]["num_thread"] == DEFAULT_NUM_THREAD
    assert sent["keep_alive"] == DEFAULT_KEEP_ALIVE
    assert "think" not in sent  # not sent unless explicitly set


@respx.mock
def test_generate_threads_think_when_set() -> None:
    route = respx.post(f"{_BASE}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "hi"})
    )
    OllamaClient(base_url=_BASE).generate(model="qwen3:8b", prompt="p", think=False)
    sent = json.loads(route.calls.last.request.content)
    assert sent["think"] is False


# ---------- structured output (12.8 Spike A) ----------

_SCHEMA = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}


@respx.mock
def test_generate_threads_format_when_set() -> None:
    route = respx.post(f"{_BASE}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": '{"x": 1}'})
    )
    OllamaClient(base_url=_BASE).generate(
        model="qwen3:8b", prompt="p", output_format=_SCHEMA
    )
    sent = json.loads(route.calls.last.request.content)
    assert sent["format"] == _SCHEMA


@respx.mock
def test_generate_omits_format_by_default() -> None:
    route = respx.post(f"{_BASE}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "hi"})
    )
    OllamaClient(base_url=_BASE).generate(model="qwen3:8b", prompt="p")
    sent = json.loads(route.calls.last.request.content)
    assert "format" not in sent


@respx.mock
async def test_generate_stream_threads_format_when_set() -> None:
    route = respx.post(f"{_BASE}/api/generate").mock(
        return_value=httpx.Response(200, content='{"response": "hi", "done": true}\n')
    )
    _ = [
        c
        async for c in OllamaClient(base_url=_BASE).generate_stream(
            model="qwen3:8b", prompt="p", output_format=_SCHEMA
        )
    ]
    sent = json.loads(route.calls.last.request.content)
    assert sent["format"] == _SCHEMA


# ---------- unload ----------

@respx.mock
async def test_generate_stream_payload_includes_calibrated_options() -> None:
    body = '{"response": "hi", "done": true}\n'
    route = respx.post(f"{_BASE}/api/generate").mock(
        return_value=httpx.Response(200, content=body)
    )
    chunks = [
        c
        async for c in OllamaClient(base_url=_BASE).generate_stream(
            model="qwen3:8b", prompt="p", operation=Operation.CHAT, prompt_tokens=200
        )
    ]
    assert chunks == ["hi"]
    sent = json.loads(route.calls.last.request.content)
    assert sent["stream"] is True
    assert sent["options"]["num_ctx"] == 2048  # downscaled from prompt_tokens
    assert sent["keep_alive"] == DEFAULT_KEEP_ALIVE


@respx.mock
def test_unload_posts_keep_alive_zero() -> None:
    route = respx.post(f"{_BASE}/api/generate").mock(
        return_value=httpx.Response(200, json={"done": True})
    )
    OllamaClient(base_url=_BASE).unload("nomic-embed-text")
    sent = json.loads(route.calls.last.request.content)
    assert sent["model"] == "nomic-embed-text"
    assert sent["keep_alive"] == 0


@respx.mock
def test_unload_swallows_errors() -> None:
    respx.post(f"{_BASE}/api/generate").mock(side_effect=httpx.ConnectError("down"))
    # Fire-and-forget: a dead daemon must not crash the generate path.
    OllamaClient(base_url=_BASE).unload("nomic-embed-text")
