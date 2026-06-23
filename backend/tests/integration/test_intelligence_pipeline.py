"""Phase 10.5 — end-to-end integration across the intelligence layer.

Composes the eight Phase 10 modules into one offline pipeline (no live Ollama):
QueryUnderstander → IndexPreprocessor → MultiVectorRetriever → BulletScorer
(context) → ReasoningEngine → SelfCorrector → ContextMemory.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

import backend.models  # noqa: F401
from backend.models.base import Base
from backend.services.intelligence.context_memory import ContextMemory
from backend.services.intelligence.index_preprocessor import IndexPreprocessor
from backend.services.intelligence.model_orchestrator import ModelOrchestrator
from backend.services.intelligence.multi_vector_retriever import MultiVectorRetriever
from backend.services.intelligence.query_understander import QueryUnderstander
from backend.services.intelligence.reasoning_engine import ReasoningEngine
from backend.services.intelligence.self_corrector import SelfCorrector
from backend.services.resume.bullet_scorer import BulletScorer


class _OfflineOllama:
    def is_available(self) -> bool:
        return False

    def generate(self, **kwargs: object) -> str:  # pragma: no cover - never called offline
        raise AssertionError("offline pipeline must not call Ollama")


class _Loader:
    def load(self, name: str) -> dict:
        return {"system": "s", "user_template": "{job_description}{evidence_json}{understood_query}"}


class _FakeRetriever:
    def __init__(self, pool: list[dict]) -> None:
        self._pool = pool

    def retrieve(self, query: str, doc_types: list[str], top_k: int = 10) -> list[dict]:
        return self._pool


def _ev(i: str, text: str, score: float, exp: str) -> dict:
    return {
        "id": i, "text": text, "semantic_score": score, "collection": "acos_experiences",
        "metadata": {"experience_id": exp, "company": "Acme", "title": "PM", "confidence_level": "verified"},
    }


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    from backend.services.tenancy import ensure_default_tenant, set_session_tenant
    set_session_tenant(s, ensure_default_tenant(s))
    yield s
    s.close()


JD = (
    "Senior Product Manager. Own the product roadmap, work cross-functionally, "
    "drive stakeholder alignment. Required: SQL, roadmapping. Preferred: Python."
)


def test_full_offline_pipeline_produces_grounded_corrected_bullets(session: Session) -> None:
    # 1. Understand the JD (offline fallback)
    qu = QueryUnderstander(_OfflineOllama(), _Loader())
    understood = qu.understand(JD)
    assert understood["role_type"] == "product_management"

    # 2. Index-time preprocessing is deterministic and composes
    pre = IndexPreprocessor()
    assert pre.preprocess("Built ML models; shipped to prod")  # smoke

    # 3. Multi-vector retrieval with MMR diversity
    pool = [
        _ev("e1", "Led SQL data migration cutting latency 40%", 0.92, "expA"),
        _ev("e2", "Led SQL data migration cutting latency 40% fast", 0.90, "expA"),  # near-dup
        _ev("e3", "Partnered cross-functionally on roadmap with stakeholders", 0.70, "expB"),
    ]
    mvr = MultiVectorRetriever(_FakeRetriever(pool), mmr_lambda=0.5)
    retrieved = mvr.retrieve(understood)
    ids = [b["evidence_id"] for b in retrieved]
    assert ids[0] == "e1"
    assert ids.index("e3") < ids.index("e2")  # diverse beats near-dup

    # 4. Context-aware scoring favors uncovered dimensions
    scorer = BulletScorer()
    scored = sorted(
        retrieved,
        key=lambda b: scorer.score_with_context(b, b["relevance_score"], covered_dimensions=set()),
        reverse=True,
    )
    assert scored

    # 5. Reasoning trace cites only real evidence ids (offline fallback recommends all)
    reasoner = ReasoningEngine(ModelOrchestrator(_OfflineOllama()), _Loader())
    trace = reasoner.reason(JD, retrieved)
    assert set(trace["recommended_evidence_ids"]).issubset({b["evidence_id"] for b in retrieved})

    # 6. Self-correction dedups and flags hallucinated skills
    corrector = SelfCorrector()
    result = corrector.correct(retrieved, allowed_skills=understood["required_skills"])
    assert len(result.bullets) < len(retrieved)  # near-dup removed

    # 7. Context memory roundtrip persists the outcome
    memory = ContextMemory(session)
    memory.record_outcome(
        role_type=understood["role_type"], company="Acme",
        content={"outcome": "interview", "bullets": result.bullets and result.bullets[0]["evidence_id"]},
    )
    recalled = memory.retrieve(role_type="product_management", company="Acme")
    assert recalled and recalled[0]["outcome"] == "interview"


def test_reasoning_never_invents_ids_across_pipeline(session: Session) -> None:
    """AC-10-5 end-to-end: no recommended id escapes the retrieved pool."""
    qu = QueryUnderstander(_OfflineOllama(), _Loader())
    understood = qu.understand(JD)
    pool = [_ev("e1", "Led SQL migration", 0.9, "expA")]
    retrieved = MultiVectorRetriever(_FakeRetriever(pool)).retrieve(understood)
    trace = ReasoningEngine(ModelOrchestrator(_OfflineOllama()), _Loader()).reason(JD, retrieved)
    pool_ids = {b["evidence_id"] for b in retrieved}
    assert all(i in pool_ids for i in trace["recommended_evidence_ids"])
