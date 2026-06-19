from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.copilot.engine import CopilotEngine, _detect_intent


def _make_rag(
    response: str = "Test response",
    evidence: list | None = None,
    confidence: str = "strong_inference",
):
    rag = MagicMock()
    rag.query.return_value = {
        "response": response,
        "evidence": evidence or [],
        "confidence_summary": confidence,
    }
    return rag


def test_detect_intent_resume():
    assert _detect_intent("Help me improve my resume") == "resume_help"


def test_detect_intent_cover_letter():
    assert _detect_intent("Write me a cover letter for this role") == "cover_letter_help"


def test_detect_intent_interview():
    assert _detect_intent("How should I prepare for the interview?") == "interview_prep"


def test_detect_intent_job_fit():
    assert _detect_intent("Am I a good fit for this job?") == "job_fit_analysis"


def test_detect_intent_career_advice():
    assert _detect_intent("What career path should I take?") == "career_advice"


def test_detect_intent_default_fallback():
    assert _detect_intent("What is the meaning of life?") == "knowledge_lookup"


def test_chat_returns_all_required_keys():
    engine = CopilotEngine(_make_rag())
    result = engine.chat("Tell me about my background")
    assert set(result.keys()) >= {"response", "intent", "confidence", "citations", "evidence_count"}


def test_chat_response_matches_rag_output():
    engine = CopilotEngine(_make_rag(response="You have 5 years of experience."))
    result = engine.chat("What is my experience?")
    assert result["response"] == "You have 5 years of experience."


def test_chat_confidence_from_rag():
    engine = CopilotEngine(_make_rag(confidence="verified"))
    result = engine.chat("Tell me my skills")
    assert result["confidence"] == "verified"


def test_chat_evidence_becomes_citations():
    evidence = [
        {
            "source": "acos_experiences",
            "text": "Led a team of engineers at Acme Corp.",
            "confidence": "verified",
            "similarity_score": 0.95,
        },
        {
            "source": "acos_projects",
            "text": "Built a machine learning pipeline.",
            "confidence": "strong_inference",
            "similarity_score": 0.80,
        },
    ]
    engine = CopilotEngine(_make_rag(evidence=evidence))
    result = engine.chat("What are my achievements?")
    assert result["evidence_count"] == 2
    assert len(result["citations"]) == 2
    assert result["citations"][0]["source"] == "acos_experiences"
    assert result["citations"][0]["confidence"] == "verified"
    assert len(result["citations"][0]["text"]) <= 150


def test_chat_caps_citations_at_five():
    evidence = [
        {"source": f"acos_{i}", "text": f"Evidence {i}", "confidence": "verified", "similarity_score": 0.9}
        for i in range(10)
    ]
    engine = CopilotEngine(_make_rag(evidence=evidence))
    result = engine.chat("Query")
    assert len(result["citations"]) == 5
    assert result["evidence_count"] == 10


def test_chat_passes_history_context_to_rag():
    rag = _make_rag()
    engine = CopilotEngine(rag)
    history = [
        {"role": "user", "content": "Tell me about my Python skills"},
        {"role": "assistant", "content": "You have 5 years of Python experience."},
    ]
    engine.chat("Can you elaborate on that?", conversation_history=history)
    call_query = rag.query.call_args[0][0]
    assert "Can you elaborate on that?" in call_query


def test_chat_no_history_still_works():
    engine = CopilotEngine(_make_rag())
    result = engine.chat("Hello", conversation_history=[])
    assert result["response"] == "Test response"


def test_chat_none_history_defaults_to_empty():
    engine = CopilotEngine(_make_rag())
    result = engine.chat("Hello", conversation_history=None)
    assert result["response"] == "Test response"


def test_chat_intent_inferred_from_message():
    rag = _make_rag()
    engine = CopilotEngine(rag)
    engine.chat("Help me with my resume")
    _, kwargs = rag.query.call_args
    assert kwargs.get("intent") == "resume_help"
