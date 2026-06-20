from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository
from backend.services.learning.ranker import OutcomeRanker

STRONG_SIGNALS = {"phone_screen", "interview", "final_round", "offer", "accepted"}
WEAK_SIGNALS = {"applied", "no_response", "rejected"}


def _rate(signals: list) -> float:
    if not signals:
        return 0.0
    strong = sum(1 for s in signals if s.signal_type in STRONG_SIGNALS)
    return round(strong / len(signals), 4)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0
    return round(cov / (vx ** 0.5 * vy ** 0.5), 4)


class Evaluator:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = OutcomeSignalRepository(session)
        self._ranker = OutcomeRanker(session)

    def interview_rate(self) -> dict:
        signals = self._repo.list()
        interviews = sum(1 for s in signals if s.signal_type in STRONG_SIGNALS)
        total = len(signals)
        return {
            "interview_rate": round(interviews / total, 4) if total else 0.0,
            "total": total,
            "interviews": interviews,
        }

    def template_effectiveness(self) -> list[dict]:
        signals = self._repo.list()
        by_template: dict[str, list] = defaultdict(list)
        for s in signals:
            by_template[s.template_used or "unknown"].append(s)
        base = {r["template_name"]: r for r in self._ranker.get_template_rankings()}
        out = []
        for template, rows in by_template.items():
            row = dict(base.get(template, {"template_name": template}))
            row["interview_rate"] = _rate(rows)
            row["sample_size"] = len(rows)
            out.append(row)
        out.sort(key=lambda r: r["interview_rate"], reverse=True)
        return out

    def ats_outcome_correlation(self) -> dict:
        base = self._ranker.get_ats_vs_outcome_correlation()
        all_signals = self._repo.list()
        xs = [float(s.ats_score) for s in all_signals if s.ats_score is not None]
        ys = [
            1.0 if s.signal_type in STRONG_SIGNALS else 0.0
            for s in all_signals
            if s.ats_score is not None
        ]
        base["correlation"] = _pearson(xs, ys)
        return base

    def industry_effectiveness(self) -> list[dict]:
        signals = self._repo.list()
        by_ind: dict[str, list] = defaultdict(list)
        for s in signals:
            if s.industry:
                by_ind[s.industry].append(s)
        out = [
            {"industry": ind, "interview_rate": _rate(rows), "sample_size": len(rows)}
            for ind, rows in by_ind.items()
        ]
        out.sort(key=lambda r: r["interview_rate"], reverse=True)
        return out
