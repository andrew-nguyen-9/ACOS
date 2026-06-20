# backend/services/optimization/ab_testing.py
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.models.base import utcnow
from backend.repositories.optimization import ABExperimentRepository, ABVariantRepository


class ABTestingService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._exp = ABExperimentRepository(session)
        self._var = ABVariantRepository(session)

    def create_experiment(self, name: str, target_engine: str,
                          variant_a: dict, variant_b: dict):
        exp = self._exp.create(name=name, target_engine=target_engine)
        self._var.create(experiment_id=exp.id, label="A", config_json=json.dumps(variant_a))
        self._var.create(experiment_id=exp.id, label="B", config_json=json.dumps(variant_b))
        self._session.flush()
        return exp

    def record_impression(self, variant_id: str) -> None:
        v = self._var.get(variant_id)
        if v is None:
            raise ValueError(f"Variant {variant_id} not found")
        v.impressions += 1
        self._session.flush()

    def record_conversion(self, variant_id: str) -> None:
        v = self._var.get(variant_id)
        if v is None:
            raise ValueError(f"Variant {variant_id} not found")
        v.conversions += 1
        self._session.flush()

    def conversion_rate(self, variant_id: str) -> float:
        v = self._var.get(variant_id)
        if v is None or v.impressions == 0:
            return 0.0
        return round(v.conversions / v.impressions, 4)

    def conclude(self, experiment_id: str):
        exp = self._exp.get(experiment_id)
        if exp is None:
            raise ValueError(f"Experiment {experiment_id} not found")
        variants = self._var.list_for_experiment(experiment_id)
        if len(variants) < 2 or any(v.impressions < 1 for v in variants):
            raise ValueError("Cannot conclude: every variant needs at least one impression.")
        # Highest conversion rate wins; ties resolved toward label 'A'.
        ranked = sorted(
            variants,
            key=lambda v: (v.conversions / v.impressions, v.label == "A"),
            reverse=True,
        )
        exp.winner_variant_id = ranked[0].id
        exp.status = "concluded"
        exp.concluded_at = utcnow()
        self._session.flush()
        return exp
