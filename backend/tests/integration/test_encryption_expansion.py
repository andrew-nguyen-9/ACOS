"""Phase 16.2 (ADR-015) — encryption extends to all sensitive fields, default OFF
unchanged, and the keymgmt-unlocked DEK drives field encryption end to end.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.config import get_settings
from backend.models.application import Application
from backend.models.experience import Experience, ExperienceBullet
from backend.models.resume import Resume
from backend.security import keymgmt
from backend.services.tenancy import require_session_tenant


@pytest.fixture
def encryption_on(monkeypatch):
    """Enable encryption with a DEK unlocked via the keymgmt KEK path (not the raw
    env key) — proves the 16.2 wiring, not just 14.3's."""
    pytest.importorskip("cryptography")
    kek = keymgmt.new_keychain_kek()
    _material, dek = keymgmt.create_key_material("pw", kek)
    keymgmt.set_active_key(dek)
    monkeypatch.setenv("ACOS_ENABLE_ENCRYPTED_STORAGE", "1")
    get_settings.cache_clear()
    yield
    keymgmt.set_active_key(None)
    get_settings.cache_clear()


def _raw(session, table, col, row_id):
    return session.execute(
        text(f"SELECT {col} FROM {table} WHERE id = :id"), {"id": row_id}
    ).scalar_one()


def test_application_fields_encrypted_at_rest(encryption_on, test_session):
    tid = require_session_tenant(test_session)
    app = Application(
        company="Acme", position="PM",
        job_description="secret-jd-keyword", recruiter_email="recruiter@corp.test",
        recruiter_name="Jane Doe", notes="comp 200k", tenant_id=tid,
    )
    test_session.add(app)
    test_session.commit()

    for col, secret in [("job_description", "secret-jd-keyword"),
                        ("recruiter_email", "recruiter@corp.test"),
                        ("recruiter_name", "Jane Doe")]:
        raw = _raw(test_session, "applications", col, app.id)
        assert secret not in raw  # ciphertext at rest

    test_session.expire_all()
    got = test_session.get(Application, app.id)
    assert got.job_description == "secret-jd-keyword"
    assert got.recruiter_email == "recruiter@corp.test"


def test_experience_career_history_encrypted(encryption_on, test_session):
    tid = require_session_tenant(test_session)
    exp = Experience(
        title="Analyst", company="X", employment_type="full_time",
        start_date="2020-01", description="led-secret-initiative", tenant_id=tid,
    )
    test_session.add(exp)
    test_session.flush()
    bullet = ExperienceBullet(experience_id=exp.id, bullet_text="drove-secret-metric")
    test_session.add(bullet)
    test_session.commit()

    assert "led-secret-initiative" not in _raw(test_session, "experiences", "description", exp.id)
    assert "drove-secret-metric" not in _raw(
        test_session, "experience_bullets", "bullet_text", bullet.id
    )
    test_session.expire_all()
    assert test_session.get(Experience, exp.id).description == "led-secret-initiative"
    assert test_session.get(ExperienceBullet, bullet.id).bullet_text == "drove-secret-metric"


def test_resume_content_json_encrypted_and_roundtrips(encryption_on, test_session):
    tid = require_session_tenant(test_session)
    content = {"header": {"name": "Secret Person"}, "skills": ["python"]}
    r = Resume(name="r1", content_json=content, tenant_id=tid)
    test_session.add(r)
    test_session.commit()

    assert "Secret Person" not in _raw(test_session, "resumes", "content_json", r.id)
    test_session.expire_all()
    assert test_session.get(Resume, r.id).content_json == content


def test_off_path_byte_identical(monkeypatch, test_session):
    """Default OFF: every converted column stores plaintext exactly as written."""
    monkeypatch.delenv("ACOS_ENABLE_ENCRYPTED_STORAGE", raising=False)
    keymgmt.set_active_key(None)
    get_settings.cache_clear()
    tid = require_session_tenant(test_session)
    app = Application(company="A", position="P", job_description="plain jd", tenant_id=tid)
    test_session.add(app)
    test_session.commit()
    assert _raw(test_session, "applications", "job_description", app.id) == "plain jd"

    r = Resume(name="r", content_json={"k": "v"}, tenant_id=tid)
    test_session.add(r)
    test_session.commit()
    # OFF JSON path stores plain JSON text.
    assert _raw(test_session, "resumes", "content_json", r.id) == '{"k": "v"}'
    get_settings.cache_clear()
