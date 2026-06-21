from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """Reason-then-write: produce a job-match reasoning trace before generation.

    The trace cites only evidence IDs from the provided pool — any IDs the LLM
    invents are filtered out (AC-10-5: no hallucinated references). When Ollama
    is unavailable or returns malformed output, falls back to recommending all
    evidence with a confidence derived from pool size.
    """

    def __init__(self, orchestrator: Any, prompt_loader: Any) -> None:
        self._orch = orchestrator
        self._loader = prompt_loader

    def reason(
        self,
        job_description: str,
        evidence: list[dict],
        understood_query: dict | None = None,
    ) -> dict:
        valid_ids = [e["evidence_id"] for e in evidence]

        if not evidence:
            return self._empty_trace()

        trace = self._llm_reason(job_description, evidence, understood_query or {})
        if trace is None:
            return self._fallback_trace(valid_ids)

        # Filter recommended ids to the actual pool — drop any hallucinated ids.
        valid_set = set(valid_ids)
        trace["recommended_evidence_ids"] = [
            i for i in trace.get("recommended_evidence_ids", []) if i in valid_set
        ]
        return trace

    # ── LLM path ──────────────────────────────────────────────────────────────

    def _llm_reason(
        self, job_description: str, evidence: list[dict], understood_query: dict
    ) -> dict | None:
        try:
            prompt = self._loader.load("intelligence/reason_job_match")
            evidence_json = json.dumps(
                [
                    {"evidence_id": e["evidence_id"], "text": e.get("bullet_text", ""),
                     "confidence": e.get("confidence", "")}
                    for e in evidence
                ],
                indent=2,
            )
            user = prompt["user_template"].format(
                job_description=job_description[:2000],
                evidence_json=evidence_json,
                understood_query=json.dumps(understood_query),
            )
            raw = self._orch.run("deep_reasoning", prompt=user, system=prompt["system"])
            if raw is None:
                return None
            data = json.loads(raw)
            return {
                "strong_matches": list(data.get("strong_matches", [])),
                "gaps": list(data.get("gaps", [])),
                "contradiction_flags": list(data.get("contradiction_flags", [])),
                "recommended_evidence_ids": list(data.get("recommended_evidence_ids", [])),
                "confidence": float(data.get("confidence", 0.5)),
            }
        except Exception as exc:
            logger.warning("reasoning_engine: LLM reason failed (%s), using fallback", exc)
            return None

    # ── Fallbacks ───────────────────────────────────────────────────────────────

    def _fallback_trace(self, valid_ids: list[str]) -> dict:
        # More evidence → higher confidence, capped at 0.6 (no reasoning performed).
        confidence = min(0.6, 0.2 + 0.1 * len(valid_ids))
        return {
            "strong_matches": [],
            "gaps": [],
            "contradiction_flags": [],
            "recommended_evidence_ids": list(valid_ids),
            "confidence": confidence,
        }

    def _empty_trace(self) -> dict:
        return {
            "strong_matches": [],
            "gaps": [],
            "contradiction_flags": [],
            "recommended_evidence_ids": [],
            "confidence": 0.0,
        }
