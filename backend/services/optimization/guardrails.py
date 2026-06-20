from __future__ import annotations

_ENGINES = {"resume", "ats", "rag", "cover_letter", "copilot"}
_CONFIDENCE = {"verified", "strong_inference", "weak_inference"}
_RISK = {"low", "medium", "high"}
_REQUIRED = (
    "target_engine", "target_parameter", "proposed_value",
    "rationale", "expected_impact", "confidence_level", "risk_level",
)
_INTERVIEW_TERMS = ("interview", "conversion", "callback", "recruiter")


class GuardrailViolation(Exception):
    pass


def validate_proposal(proposal: dict) -> None:
    for field in _REQUIRED:
        value = proposal.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise GuardrailViolation(f"Missing required field: {field}")

    if proposal["confidence_level"] not in _CONFIDENCE:
        raise GuardrailViolation(f"Invalid confidence_level: {proposal['confidence_level']}")
    if proposal["risk_level"] not in _RISK:
        raise GuardrailViolation(f"Invalid risk_level: {proposal['risk_level']}")
    if proposal["target_engine"] not in _ENGINES:
        raise GuardrailViolation(f"Invalid target_engine: {proposal['target_engine']}")

    if proposal["target_engine"] == "ats":
        text = f"{proposal['rationale']} {proposal['expected_impact']}".lower()
        mentions_ats = "ats score" in text or "ats_score" in text
        mentions_interview = any(term in text for term in _INTERVIEW_TERMS)
        if mentions_ats and not mentions_interview:
            raise GuardrailViolation(
                "ATS proposal justified by ATS score alone; primary objective is interview rate."
            )

    if proposal["risk_level"] == "high" and proposal["confidence_level"] == "weak_inference":
        raise GuardrailViolation("High-risk proposals require stronger than weak_inference confidence.")
