# backend/services/optimization/recommender.py
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.repositories.optimization import OptimizationProposalRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.optimization.evaluator import Evaluator
from backend.services.optimization.guardrails import validate_proposal, GuardrailViolation


class Recommender:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._eval = Evaluator(session)
        self._proposals = OptimizationProposalRepository(session)
        self._config = SystemConfigRepository(session)

    def _persist(self, candidate: dict):
        try:
            validate_proposal(candidate)
        except GuardrailViolation:
            return None
        return self._proposals.create(**candidate)

    def generate_proposals(self, min_sample_size: int = 5) -> list:
        created = []

        # Heuristic 1: template switch
        templates = [t for t in self._eval.template_effectiveness()
                     if t.get("sample_size", 0) >= min_sample_size]
        if len(templates) >= 2:
            best, worst = templates[0], templates[-1]
            gap = best["interview_rate"] - worst["interview_rate"]
            if gap >= 0.15:
                both_large = best["sample_size"] >= 10 and worst["sample_size"] >= 10
                pct = round(gap * 100)
                c = self._persist({
                    "target_engine": "resume",
                    "target_parameter": "default_template",
                    "current_value": worst["template_name"],
                    "proposed_value": best["template_name"],
                    "rationale": (
                        f"Template '{best['template_name']}' shows a "
                        f"{best['interview_rate']:.0%} interview rate vs "
                        f"'{worst['template_name']}' at {worst['interview_rate']:.0%}."
                    ),
                    "expected_impact": f"~{pct}% higher interview rate by switching default template.",
                    "confidence_level": "strong_inference" if both_large else "weak_inference",
                    "risk_level": "low",
                    "evidence_json": json.dumps({"templates": templates}),
                })
                if c:
                    created.append(c)

        # Heuristic 2: ATS recalibration (justified by interview rate)
        corr = self._eval.ats_outcome_correlation()
        total = corr.get("total_signals", 0)
        if total >= min_sample_size and corr["correlation"] < 0.1:
            current = self._config.get_value("ats_keyword_weight", "0.35") or "0.35"
            new_val = max(0.1, round(float(current) - 0.05, 2))
            c = self._persist({
                "target_engine": "ats",
                "target_parameter": "ats_keyword_weight",
                "current_value": current,
                "proposed_value": str(new_val),
                "rationale": (
                    "ATS score shows near-zero correlation with interview outcomes "
                    f"(r={corr['correlation']}); reducing keyword weight should improve "
                    "readability without hurting the interview rate."
                ),
                "expected_impact": "Neutral-to-positive interview rate; better human readability.",
                "confidence_level": "weak_inference",
                "risk_level": "medium",
                "evidence_json": json.dumps(corr),
            })
            if c:
                created.append(c)

        # Heuristic 3: industry emphasis
        for ind in self._eval.industry_effectiveness():
            if ind["sample_size"] >= min_sample_size and ind["interview_rate"] >= 0.5:
                c = self._persist({
                    "target_engine": "resume",
                    "target_parameter": f"industry_emphasis::{ind['industry']}",
                    "current_value": None,
                    "proposed_value": "increase",
                    "rationale": (
                        f"{ind['industry']} roles convert at "
                        f"{ind['interview_rate']:.0%} interview rate "
                        f"(n={ind['sample_size']}); emphasize matching experience."
                    ),
                    "expected_impact": f"Higher interview rate for {ind['industry']} applications.",
                    "confidence_level": "strong_inference",
                    "risk_level": "low",
                    "evidence_json": json.dumps(ind),
                })
                if c:
                    created.append(c)

        return created
