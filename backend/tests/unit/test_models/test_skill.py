from backend.models.skill import Skill, SkillEvidence


def test_skill_created_with_defaults(test_session):
    skill = Skill(name="Python", category="programming")
    test_session.add(skill)
    test_session.flush()

    assert skill.id is not None
    assert skill.proficiency == "intermediate"
    assert skill.created_at is not None


def test_skill_name_must_be_unique(test_session):
    s1 = Skill(name="SQL", category="data")
    s2 = Skill(name="SQL", category="data")
    test_session.add(s1)
    test_session.flush()
    test_session.add(s2)

    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        test_session.flush()


def test_skill_evidence_links_to_skill(test_session):
    skill = Skill(name="GCP", category="tool")
    test_session.add(skill)
    test_session.flush()

    ev = SkillEvidence(
        skill_id=skill.id,
        source_type="experience",
        source_id="fake-exp-id",
        evidence_text="Leveraged GCP for data analysis",
        confidence_level="verified",
    )
    test_session.add(ev)
    test_session.flush()

    assert ev.skill_id == skill.id
    assert ev.confidence_level == "verified"


def test_skill_evidence_cascade_delete(test_session):
    skill = Skill(name="Tableau", category="tool")
    ev = SkillEvidence(
        source_type="experience",
        source_id="x",
        evidence_text="Built dashboards",
        confidence_level="verified",
    )
    skill.evidence.append(ev)
    test_session.add(skill)
    test_session.flush()

    ev_id = ev.id
    test_session.delete(skill)
    test_session.flush()

    assert test_session.get(SkillEvidence, ev_id) is None
