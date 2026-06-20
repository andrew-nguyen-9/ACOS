from __future__ import annotations

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.optimization.evaluator import Evaluator
from backend.services.optimization.recommender import Recommender


class LearningLoop:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._outcomes = OutcomeSignalRepository(session)
        self._config = SystemConfigRepository(session)
        self._eval = Evaluator(session)
        self._rec = Recommender(session)

    def _application_count(self) -> int:
        return len({s.application_id for s in self._outcomes.list()})

    def _trigger_count(self) -> int:
        raw = self._config.get_value("learning_trigger_count", "5") or "5"
        try:
            return max(1, int(raw))
        except ValueError:
            return 5

    def should_run(self) -> bool:
        count = self._application_count()
        trigger = self._trigger_count()
        return count > 0 and count % trigger == 0

    def run(self) -> dict:
        metrics = {
            "interview_rate": self._eval.interview_rate(),
            "template_effectiveness": self._eval.template_effectiveness(),
            "ats_outcome_correlation": self._eval.ats_outcome_correlation(),
            "industry_effectiveness": self._eval.industry_effectiveness(),
        }
        created = self._rec.generate_proposals(min_sample_size=self._trigger_count())
        return {
            "ran": True,
            "metrics": metrics,
            "proposals_created": len(created),
            "proposal_ids": [p.id for p in created],
        }

    def maybe_run(self) -> dict:
        if not self.should_run():
            return {"ran": False, "reason": "trigger threshold not reached"}
        return self.run()
