from __future__ import annotations

import pytest

from backend.services.intelligence.model_orchestrator import ModelOrchestrator


class _SpyOllama:
    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.calls: list[dict] = []

    def is_available(self) -> bool:
        return self._available

    def generate(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return "ok"


def test_fast_retrieval_uses_zero_temperature() -> None:
    spy = _SpyOllama()
    orch = ModelOrchestrator(spy)

    orch.run("fast_retrieval", prompt="q", system="s")

    assert spy.calls[0]["temperature"] == 0.0


def test_copilot_uses_higher_temperature_than_reasoning() -> None:
    spy = _SpyOllama()
    orch = ModelOrchestrator(spy)

    orch.run("copilot", prompt="q")
    orch.run("deep_reasoning", prompt="q")

    assert spy.calls[0]["temperature"] > spy.calls[1]["temperature"]


def test_unknown_mode_raises() -> None:
    orch = ModelOrchestrator(_SpyOllama())
    with pytest.raises(ValueError):
        orch.run("nonsense_mode", prompt="q")


def test_passes_prompt_and_system_through() -> None:
    spy = _SpyOllama()
    orch = ModelOrchestrator(spy)

    orch.run("ats_optimization", prompt="the prompt", system="the system")

    assert spy.calls[0]["prompt"] == "the prompt"
    assert spy.calls[0]["system"] == "the system"


def test_returns_none_when_unavailable() -> None:
    orch = ModelOrchestrator(_SpyOllama(available=False))
    assert orch.run("deep_reasoning", prompt="q") is None
