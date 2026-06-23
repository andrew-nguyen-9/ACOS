"""Phase 12.14 cross-store isolation: SQLite + Chroma + the flywheel signal table.

No store may leak tenant A's data into tenant B's reads.
"""
from __future__ import annotations

from backend.rag.chroma_client import ChromaManager
from backend.rag.indexer import RAGIndexer
from backend.rag.retriever import RAGRetriever
from backend.services.flywheel.feedback import FeedbackEngine
from backend.services.rag import lexical
from backend.services.tenancy import ensure_tenant, set_session_tenant


class _FakeEmbedder:
    """Deterministic 3-dim vector so both tenants' docs collide on similarity —
    forcing the tenant filter (not the distance) to do the isolating."""

    def embed(self, text):
        return [0.1, 0.2, 0.3]

    def embed_batch(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


def test_chroma_query_is_tenant_scoped(tmp_path):
    """A Chroma query carrying tenant t1 never returns t2's vectors."""
    mgr = ChromaManager(str(tmp_path))
    col = "tenant_iso"
    mgr.add(col, ids=["a"], documents=["alpha"], embeddings=[[0.1, 0.2, 0.3]],
            metadatas=[{"doc_type": "exp"}], tenant_id="t1")
    mgr.add(col, ids=["b"], documents=["beta"], embeddings=[[0.1, 0.2, 0.3]],
            metadatas=[{"doc_type": "exp"}], tenant_id="t2")

    res = mgr.query(col, query_embeddings=[[0.1, 0.2, 0.3]], n_results=10, tenant_id="t1")
    assert res["ids"][0] == ["a"]  # only t1's vector


def test_chroma_where_composes_with_doc_type(tmp_path):
    """Tenant filter ANDs with the 12.6 doc_type where, not replaces it."""
    mgr = ChromaManager(str(tmp_path))
    col = "tenant_iso2"
    mgr.add(col, ids=["a"], documents=["x"], embeddings=[[0.1, 0.2, 0.3]],
            metadatas=[{"doc_type": "exp"}], tenant_id="t1")
    mgr.add(col, ids=["b"], documents=["y"], embeddings=[[0.1, 0.2, 0.3]],
            metadatas=[{"doc_type": "proj"}], tenant_id="t1")
    res = mgr.query(col, query_embeddings=[[0.1, 0.2, 0.3]], n_results=10,
                    tenant_id="t1", where={"doc_type": "exp"})
    assert res["ids"][0] == ["a"]


def test_signals_isolated_by_tenant(test_session):
    ensure_tenant(test_session, "t1")
    ensure_tenant(test_session, "t2")
    eng = FeedbackEngine(test_session)
    set_session_tenant(test_session, "t1")
    eng.record_signal(entity_type="skill", entity_id="python", signal_type="skill_used",
                      value=1.0, source={"table": "resumes", "ids": ["app1"]})
    set_session_tenant(test_session, "t2")
    eng.record_signal(entity_type="skill", entity_id="rust", signal_type="skill_used",
                      value=1.0, source={"table": "resumes", "ids": ["app2"]})

    set_session_tenant(test_session, "t1")
    t1 = eng.rollup(tenant_id="t1")["aggregates"]
    assert {a["entity_id"] for a in t1} == {"python"}


def test_route_isolation_via_session(unauth_client, test_session):
    """The ROI route, driven by two authenticated sessions (ADR-014, not a header),
    sees only the calling session's tenant signals. Header-selection is gone — a
    session's bound tenant is the only selector."""
    from backend.services import auth as auth_service

    auth_service.enroll(test_session, "pw1", tenant_id="t1")
    auth_service.enroll(test_session, "pw2", tenant_id="t2")
    t1_token = auth_service.login(test_session, "pw1", tenant_id="t1")
    t2_token = auth_service.login(test_session, "pw2", tenant_id="t2")
    eng = FeedbackEngine(test_session)
    # t1: python used in 6 apps with outcomes -> a real ROI
    set_session_tenant(test_session, "t1")
    for i, (stype, w) in enumerate(
        [("interview", 0.7), ("offer", 1.0), ("rejected", 0.1),
         ("interview", 0.7), ("phone_screen", 0.4), ("final_round", 0.85),
         ("no_response", 0.0)]
    ):
        app = f"app{i}"
        eng.record_signal(entity_type="application", entity_id=app, signal_type=stype,
                          value=w, source={"table": "outcome_signals", "ids": [f"os{i}"]})
        if i < 6:
            eng.record_signal(entity_type="skill", entity_id="python", signal_type="skill_used",
                              value=1.0, source={"table": "resumes", "ids": [app]})
    # t2: only rust, no outcomes -> empty ROI
    set_session_tenant(test_session, "t2")
    eng.record_signal(entity_type="skill", entity_id="rust", signal_type="skill_used",
                      value=1.0, source={"table": "resumes", "ids": ["z1"]})
    test_session.commit()

    r1 = unauth_client.get("/api/v1/flywheel/skills/roi",
                           headers={"Authorization": f"Bearer {t1_token}"})
    assert r1.status_code == 200
    assert r1.json()["recommended"] == ["python"]

    r2 = unauth_client.get("/api/v1/flywheel/skills/roi",
                           headers={"Authorization": f"Bearer {t2_token}"})
    assert r2.status_code == 200
    assert r2.json()["skills"] == []  # t2 has no python, no outcomes


def _index_as(session, mgr, doc_id, tenant, text):
    ensure_tenant(session, tenant)
    set_session_tenant(session, tenant)
    RAGIndexer(mgr, _FakeEmbedder(), session=session).index_document(
        doc_id, text, {}, doc_type="acos_experiences"
    )


def test_rag_retriever_scopes_chroma_to_session_tenant(tmp_path, test_session):
    """C1: the real RAGRetriever (session-bound) never returns another tenant's vectors."""
    mgr = ChromaManager(str(tmp_path))
    _index_as(test_session, mgr, "d1", "t1", "python sql roadmap experience")
    _index_as(test_session, mgr, "d2", "t2", "python sql roadmap experience")

    set_session_tenant(test_session, "t1")
    retriever = RAGRetriever(mgr, _FakeEmbedder(), session=test_session)
    results = retriever.retrieve("python", ["acos_experiences"], top_k=10)
    assert {r["id"] for r in results} == {"d1"}  # t2's d2 excluded


def test_lexical_search_scopes_fts_to_tenant(tmp_path, test_session):
    """C2: the FTS5 lexical leg (raw SQL) is tenant-filtered on read."""
    mgr = ChromaManager(str(tmp_path))
    _index_as(test_session, mgr, "d1", "t1", "python sql roadmap experience")
    _index_as(test_session, mgr, "d2", "t2", "python sql roadmap experience")

    set_session_tenant(test_session, "t1")
    hits = lexical.search(test_session, "python", ["acos_experiences"], tenant_id="t1")
    assert {h["id"] for h in hits} == {"d1"}


def test_memory_is_tenant_isolated(test_session):
    """16.5: agent memory (Memory) never bleeds across tenants — A cannot read B's."""
    from backend.models.memory import Memory

    ensure_tenant(test_session, "t1")
    ensure_tenant(test_session, "t2")
    set_session_tenant(test_session, "t2")
    test_session.add(Memory(memory_type="long_term", content_json='{"x": "t2-secret"}'))
    test_session.flush()

    set_session_tenant(test_session, "t1")
    # A query under t1 sees nothing of t2's memory (auto-filter, 12.14).
    assert test_session.query(Memory).all() == []


def test_no_shared_embeddings_across_tenants(tmp_path, test_session):
    """18.6 alpha safe-mode: two tenants indexing IDENTICAL text get separate,
    non-shared vectors — t1's retrieval never surfaces t2's embedding."""
    mgr = ChromaManager(str(tmp_path))
    _index_as(test_session, mgr, "e1", "t1", "identical resume text python sql")
    _index_as(test_session, mgr, "e2", "t2", "identical resume text python sql")

    set_session_tenant(test_session, "t1")
    retriever = RAGRetriever(mgr, _FakeEmbedder(), session=test_session)
    results = retriever.retrieve("python", ["acos_experiences"], top_k=10)
    assert {r["id"] for r in results} == {"e1"}  # t2's identical-text vector excluded


def test_cross_tenant_application_read_is_impossible(test_session):
    """16.5 load-bearing: tenant A cannot read tenant B's application rows."""
    from backend.models.application import Application

    ensure_tenant(test_session, "t1")
    ensure_tenant(test_session, "t2")
    set_session_tenant(test_session, "t2")
    test_session.add(Application(company="SecretCo", position="PM"))
    test_session.flush()

    set_session_tenant(test_session, "t1")
    assert test_session.query(Application).all() == []  # zero leakage


def test_tenant_migration_round_trip(tmp_path, monkeypatch):
    """I1: the schema mutation (nullable->backfill->NOT NULL+FK) runs only in prod —
    cover upgrade head + downgrade base on a temp DB."""
    import sqlite3

    from alembic import command
    from alembic.config import Config

    from backend.config import get_settings

    db = tmp_path / "mig.db"
    monkeypatch.setenv("ACOS_DB_PATH", str(db))
    get_settings.cache_clear()
    try:
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
        con = sqlite3.connect(db)
        assert con.execute("SELECT id FROM tenants").fetchall() == [("default",)]
        # tenant_id is NOT NULL on a backfilled owned table (PRAGMA notnull == 1)
        notnull = {r[1]: r[3] for r in con.execute("PRAGMA table_info(experiences)")}
        assert notnull["tenant_id"] == 1
        signal_notnull = {r[1]: r[3] for r in con.execute("PRAGMA table_info(signals)")}
        assert signal_notnull["tenant_id"] == 1
        con.close()
        command.downgrade(cfg, "base")
    finally:
        get_settings.cache_clear()
