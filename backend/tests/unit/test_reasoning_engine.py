from __future__ import annotations

import json

import pytest

from backend.services.intelligence.reasoning_engine import ReasoningEngine


class _FakeOrchestrator:
    def __init__(self, response: str | None) -> None:
        self._response = response
        self.calls: list[dict] = []

    def run(self, mode: str, prompt: str, system: str | None = None) -> str | None:
        self.calls.append({"mode": mode, "prompt": prompt})
        return self._response


class _Loader:
    def load(self, name: str) -> dict:
        return {"system": "sys", "user_template": "JD:{job_description} EV:{evidence_json} Q:{understood_query}"}


EVIDENCE = [
    {"evidence_id": "e1", "bullet_text": "Led SQL migration", "confidence": "verified"},
    {"evidence_id": "e2", "bullet_text": "Built ML pipeline", "confidence": "strong_inference"},
    {"evidence_id": "e3", "bullet_text": "Managed roadmap", "confidence": "verified"},
]


def _trace(**over: object) -> str:
    base = {
        "strong_matches": ["e1 maps to SQL requirement"],
        "gaps": ["no leadership evidence"],
        "contradiction_flags": [],
        "recommended_evidence_ids": ["e1", "e3"],
        "confidence": 0.8,
    }
    base.update(over)
    return json.dumps(base)


def test_llm_path_parses_trace() -> None:
    eng = ReasoningEngine(_FakeOrchestrator(_trace()), _Loader())
    out = eng.reason("a senior PM job", EVIDENCE)
    assert out["recommended_evidence_ids"] == ["e1", "e3"]
    assert out["confidence"] == 0.8


def test_recommended_ids_filtered_to_evidence_pool() -> None:
    # LLM hallucinates e99 which is not in the evidence pool — must be dropped
    eng = ReasoningEngine(
        _FakeOrchestrator(_trace(recommended_evidence_ids=["e1", "e99", "e3"])), _Loader()
    )
    out = eng.reason("job", EVIDENCE)
    assert "e99" not in out["recommended_evidence_ids"]
    assert out["recommended_evidence_ids"] == ["e1", "e3"]


def test_uses_deep_reasoning_mode() -> None:
    orch = _FakeOrchestrator(_trace())
    ReasoningEngine(orch, _Loader()).reason("job", EVIDENCE)
    assert orch.calls[0]["mode"] == "deep_reasoning"


def test_malformed_json_falls_back() -> None:
    eng = ReasoningEngine(_FakeOrchestrator("not json"), _Loader())
    out = eng.reason("job", EVIDENCE)
    # fallback recommends all evidence ids
    assert set(out["recommended_evidence_ids"]) == {"e1", "e2", "e3"}


def test_unavailable_orchestrator_falls_back() -> None:
    eng = ReasoningEngine(_FakeOrchestrator(None), _Loader())
    out = eng.reason("job", EVIDENCE)
    assert set(out["recommended_evidence_ids"]) == {"e1", "e2", "e3"}
    assert 0.0 <= out["confidence"] <= 1.0


def test_empty_evidence_low_confidence_no_recommendations() -> None:
    eng = ReasoningEngine(_FakeOrchestrator(None), _Loader())
    out = eng.reason("job", [])
    assert out["recommended_evidence_ids"] == []
    assert out["confidence"] == 0.0
