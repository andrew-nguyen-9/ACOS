from __future__ import annotations

import pytest
from backend.repositories.question import QuestionRepository, AnswerRepository
from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.application import ApplicationRepository


def _make_question(session, template="Tell me about {{company}}.", category="behavioral"):
    repo = QuestionRepository(session)
    return repo.create(
        question_template=template,
        category=category,
        length_target="medium",
        variables=["company"],
        source="generated",
    )


def _make_app(session):
    repo = ApplicationRepository(session)
    return repo.create(company="Acme", position="Engineer")


def test_question_repo_get_by_category(test_session):
    _make_question(test_session, category="behavioral")
    _make_question(test_session, category="technical")
    repo = QuestionRepository(test_session)
    behavioral = repo.get_by_category("behavioral")
    assert len(behavioral) == 1
    assert behavioral[0].category == "behavioral"


def test_question_repo_get_by_source(test_session):
    repo = QuestionRepository(test_session)
    repo.create(
        question_template="Manual question", category="behavioral",
        length_target="medium", variables=[], source="manual",
    )
    _make_question(test_session)  # source="generated"
    manual = repo.get_by_source("manual")
    assert len(manual) == 1


def test_answer_repo_get_by_question(test_session):
    q = _make_question(test_session)
    a_repo = AnswerRepository(test_session)
    a_repo.create(
        question_id=q.id,
        original_answer="My answer",
        confidence_level="verified",
        evidence_ids=[],
    )
    answers = a_repo.get_by_question(q.id)
    assert len(answers) == 1
    assert answers[0].original_answer == "My answer"


def test_answer_repo_get_by_application(test_session):
    q = _make_question(test_session)
    app = _make_app(test_session)
    a_repo = AnswerRepository(test_session)
    a_repo.create(
        question_id=q.id,
        application_id=app.id,
        original_answer="Context answer",
        confidence_level="strong_inference",
        evidence_ids=[],
    )
    answers = a_repo.get_by_application(app.id)
    assert len(answers) == 1


def test_answer_repo_get_latest(test_session):
    q = _make_question(test_session)
    a_repo = AnswerRepository(test_session)
    a_repo.create(
        question_id=q.id, original_answer="First", confidence_level="verified", evidence_ids=[]
    )
    a_repo.create(
        question_id=q.id, original_answer="Second", confidence_level="verified", evidence_ids=[]
    )
    latest = a_repo.get_latest(q.id)
    assert latest is not None


def test_answer_repo_get_latest_no_answers(test_session):
    q = _make_question(test_session)
    a_repo = AnswerRepository(test_session)
    assert a_repo.get_latest(q.id) is None


def test_outcome_signal_repo_get_by_application(test_session):
    app = _make_app(test_session)
    repo = OutcomeSignalRepository(test_session)
    repo.create(application_id=app.id, signal_type="interview", signal_weight=0.7)
    results = repo.get_by_application(app.id)
    assert len(results) == 1
    assert results[0].signal_type == "interview"


def test_outcome_signal_repo_get_by_signal_type(test_session):
    app1 = _make_app(test_session)
    app2 = ApplicationRepository(test_session).create(company="B", position="P")
    repo = OutcomeSignalRepository(test_session)
    repo.create(application_id=app1.id, signal_type="offer", signal_weight=1.0)
    repo.create(application_id=app2.id, signal_type="rejected", signal_weight=0.1)
    offers = repo.get_by_signal_type("offer")
    assert len(offers) == 1
    assert offers[0].signal_type == "offer"
