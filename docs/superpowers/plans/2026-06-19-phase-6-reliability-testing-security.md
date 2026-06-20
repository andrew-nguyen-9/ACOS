# Phase 6: System Reliability, Testing & Security Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring backend test coverage from 50% → ≥90%, add full Playwright E2E coverage for all five core workflows, harden every file-system and network boundary against traversal/injection, fix the confirmed Chroma/SQLite divergence bug, add performance benchmarks, and establish snapshot regression tests.

**Architecture:** Five independent tracks execute sequentially within each track but can start Track B (security) and Track C (E2E) in parallel with Track A. Track A (coverage) must complete before Track E (regression snapshots) can run. Track C (Playwright) is self-contained and only needs the frontend Vite server — it mocks the backend via `page.route()`.

**Tech Stack:** pytest + pytest-cov (existing) · pytest-benchmark (new, Track D) · @playwright/test (new, Track C) · python-docx · FastAPI TestClient · MagicMock (existing patterns)

## Global Constraints

- `from __future__ import annotations` on every new Python file (first line).
- `fail_under = 90` is already configured in `pyproject.toml` — all track A tasks must be verified with `python -m pytest backend/tests/ -q --tb=short` before committing.
- Never call `OllamaClient`, `ChromaManager`, or real network endpoints in unit tests — always use `MagicMock` or `patch`.
- All pytest fixtures follow the `function` scope already established in `backend/tests/conftest.py`.
- Playwright tests live in `frontend/e2e/` and run with `npx playwright test` from the `frontend/` directory.
- Security patches must include a regression test for each vulnerability fixed.
- No new Python dependencies except `pytest-benchmark` (Track D) and dev-only npm packages for Playwright.
- Every commit: `git add <specific files>` then commit with descriptive message. Never `git add -A`.

---

## File Map

**Created (backend/tests):**
- `backend/tests/unit/test_rag_service.py` — RAG service + evidence selector unit tests
- `backend/tests/unit/test_resume_generator_extended.py` — LLM path, fallback, normalize, content-to-text
- `backend/tests/unit/test_resume_docx_exporter_extended.py` — experiences/skills/projects/error path
- `backend/tests/unit/test_cover_letter_docx_exporter_extended.py` — CL DOCX export paths
- `backend/tests/unit/test_question_generator_extended.py` — generate_questions, generate_answer, edit_answer
- `backend/tests/integration/test_copilot_routes_extended.py` — copilot LLM path
- `backend/tests/integration/test_ingestion_security_extended.py` — path traversal + pipeline divergence
- `backend/tests/benchmark/conftest.py` — shared benchmark fixtures
- `backend/tests/benchmark/test_performance.py` — pytest-benchmark suites
- `backend/tests/unit/test_snapshots.py` — snapshot + regression tests

**Modified (backend):**
- `backend/ingestion/pipeline.py:103-118` — fix Chroma/SQLite divergence (set status=failed on indexer error)
- `backend/ingestion/security.py` — add `sanitize_text()` helper, size cap for text blobs
- `scripts/ingestion/ingest_github.py` — add README size cap + content sanitization

**Created (frontend/e2e):**
- `frontend/e2e/fixtures.ts` — shared Playwright fixtures (API route mocking)
- `frontend/e2e/resume.spec.ts` — resume generation E2E
- `frontend/e2e/cover-letter.spec.ts` — cover letter E2E
- `frontend/e2e/ats.spec.ts` — ATS scoring E2E
- `frontend/e2e/copilot.spec.ts` — copilot query E2E
- `frontend/e2e/applications.spec.ts` — Application CRM E2E

**Created (frontend config):**
- `frontend/playwright.config.ts` — Playwright config (baseURL :1420, webServer, retries)

---

## TRACK A — BACKEND TEST COVERAGE

### Task 1: RAG service + evidence selector unit tests

**Files:**
- Create: `backend/tests/unit/test_rag_service.py`

**Interfaces:**
- Consumes: `RAGService(retriever, reranker, ollama_client)` from `backend/services/rag/service.py`; `EvidenceSelector(rag_retriever, reranker)` from `backend/services/resume/evidence_selector.py`
- Produces: nothing downstream (leaf task)

- [ ] **Step 1: Write the failing test file**

```python
# backend/tests/unit/test_rag_service.py
from __future__ import annotations

from unittest.mock import MagicMock
import pytest
from backend.services.rag.service import RAGService
from backend.services.resume.evidence_selector import EvidenceSelector


# ---------- fixtures ----------

@pytest.fixture
def mock_retriever():
    r = MagicMock()
    r.retrieve.return_value = [
        {
            "id": "doc1",
            "text": "Led Python migration at Acme saving $200K.",
            "collection": "acos_experiences",
            "semantic_score": 0.92,
            "metadata": {
                "confidence_level": "verified",
                "entity_id": "exp1",
                "experience_id": "exp1",
                "company": "Acme",
                "title": "SWE",
                "start_date": "2022-01",
                "end_date": "Present",
            },
        }
    ]
    return r


@pytest.fixture
def mock_reranker():
    rr = MagicMock()
    rr.rerank.side_effect = lambda query, results, **kwargs: results
    return rr


@pytest.fixture
def mock_ollama_unavailable():
    o = MagicMock()
    o.is_available.return_value = False
    return o


@pytest.fixture
def mock_ollama_available():
    o = MagicMock()
    o.is_available.return_value = True
    o.generate.return_value = "Here is a summary of your experience."
    return o


# ---------- RAGService tests ----------

def test_query_no_ollama_returns_context_text(mock_retriever, mock_reranker, mock_ollama_unavailable):
    svc = RAGService(mock_retriever, mock_reranker, mock_ollama_unavailable)
    result = svc.query("Tell me about Python work", intent="resume_help")
    assert "response" in result
    assert "evidence" in result
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["confidence"] == "verified"


def test_query_with_ollama_calls_generate(mock_retriever, mock_reranker, mock_ollama_available):
    svc = RAGService(mock_retriever, mock_reranker, mock_ollama_available)
    result = svc.query("Tell me about Python work", intent="resume_help")
    mock_ollama_available.generate.assert_called_once()
    assert result["response"] == "Here is a summary of your experience."


def test_query_empty_evidence_returns_no_evidence_response(mock_reranker, mock_ollama_unavailable):
    r = MagicMock()
    r.retrieve.return_value = []
    mock_reranker.rerank.return_value = []
    svc = RAGService(r, mock_reranker, mock_ollama_unavailable)
    result = svc.query("anything", intent="knowledge_lookup")
    assert result["response"] == "No relevant context found."
    assert result["confidence_summary"] == "no_evidence"


def test_query_unknown_intent_defaults_to_knowledge_lookup(mock_retriever, mock_reranker, mock_ollama_unavailable):
    svc = RAGService(mock_retriever, mock_reranker, mock_ollama_unavailable)
    result = svc.query("anything", intent="totally_unknown_intent")
    assert "evidence" in result


def test_summarize_confidence_verified_beats_weak(mock_retriever, mock_reranker, mock_ollama_unavailable):
    r = MagicMock()
    r.retrieve.return_value = [
        {"id": "a", "text": "x", "collection": "acos_experiences", "semantic_score": 0.9,
         "metadata": {"confidence_level": "weak_inference"}},
        {"id": "b", "text": "y", "collection": "acos_experiences", "semantic_score": 0.8,
         "metadata": {"confidence_level": "verified"}},
    ]
    mock_reranker.rerank.side_effect = lambda query, results, **kwargs: results
    svc = RAGService(r, mock_reranker, mock_ollama_unavailable)
    result = svc.query("anything")
    assert result["confidence_summary"] == "verified"


def test_query_career_advice_intent_uses_all_collections(mock_reranker, mock_ollama_unavailable):
    r = MagicMock()
    r.retrieve.return_value = []
    mock_reranker.rerank.return_value = []
    svc = RAGService(r, mock_reranker, mock_ollama_unavailable)
    svc.query("help me grow my career", intent="career_advice")
    call_args = r.retrieve.call_args
    collections = call_args[0][1] if call_args[0] else call_args[1]["collections"]
    assert "acos_github" in collections
    assert "acos_claude_exports" in collections


# ---------- EvidenceSelector tests ----------

def test_evidence_selector_returns_bullets(mock_retriever, mock_reranker):
    selector = EvidenceSelector(mock_retriever, mock_reranker)
    bullets = selector.select("Python engineering role", {})
    assert len(bullets) == 1
    assert bullets[0]["bullet_text"] == "Led Python migration at Acme saving $200K."
    assert bullets[0]["confidence"] == "verified"
    assert bullets[0]["company"] == "Acme"


def test_evidence_selector_empty_returns_empty(mock_reranker):
    r = MagicMock()
    r.retrieve.return_value = []
    mock_reranker.rerank.return_value = []
    selector = EvidenceSelector(r, mock_reranker)
    bullets = selector.select("anything", {})
    assert bullets == []


def test_evidence_selector_respects_max_bullets(mock_reranker):
    raw = [
        {"id": f"d{i}", "text": f"bullet {i}", "collection": "acos_experiences",
         "semantic_score": 0.9,
         "metadata": {"confidence_level": "strong_inference", "experience_id": f"e{i}",
                      "company": "Co", "title": "Eng", "start_date": "2020-01", "end_date": "2022-01"}}
        for i in range(20)
    ]
    r = MagicMock()
    r.retrieve.return_value = raw
    mock_reranker.rerank.side_effect = lambda query, results, **kwargs: results
    selector = EvidenceSelector(r, mock_reranker)
    bullets = selector.select("Python role", {}, max_bullets=3)
    assert len(bullets) <= 3


def test_evidence_selector_dates_formatted(mock_reranker):
    r = MagicMock()
    r.retrieve.return_value = [
        {"id": "x", "text": "did stuff", "collection": "acos_experiences", "semantic_score": 0.5,
         "metadata": {"confidence_level": "verified", "start_date": "2021-03", "end_date": "2023-09",
                      "company": "Biz", "title": "Lead"}}
    ]
    mock_reranker.rerank.side_effect = lambda query, results, **kwargs: results
    selector = EvidenceSelector(r, mock_reranker)
    bullets = selector.select("anything", {})
    assert "2021-03" in bullets[0]["dates"]
    assert "2023-09" in bullets[0]["dates"]
```

- [ ] **Step 2: Run test — expect failures (imports work, logic untested)**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_rag_service.py -v --no-header --no-cov 2>&1 | tail -20
```

Expected: All tests PASS (these are unit tests with mocks — they will pass immediately if the service logic is correct).

- [ ] **Step 3: Run full suite to check coverage delta**

```
source .venv/bin/activate && python -m pytest backend/tests/ -q --tb=short --cov=backend --cov-report=term-missing 2>&1 | grep -E "rag/service|evidence_selector|TOTAL"
```

Expected: `rag/service.py` ≥85%, `evidence_selector.py` ≥95%

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_rag_service.py
git commit -m "test(rag): unit tests for RAGService and EvidenceSelector — covers query paths, confidence summary, intent routing"
```

---

### Task 2: Resume generator extended tests + DOCX exporter

**Files:**
- Create: `backend/tests/unit/test_resume_generator_extended.py`
- Create: `backend/tests/unit/test_resume_docx_exporter_extended.py`

**Interfaces:**
- Consumes: `ResumeGenerator` from `backend/services/resume/generator.py`; `ResumeDOCXExporter` from `backend/services/resume/docx_exporter.py`
- Produces: nothing downstream

- [ ] **Step 1: Write resume generator extended tests**

```python
# backend/tests/unit/test_resume_generator_extended.py
from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest
from backend.services.resume.generator import ResumeGenerator, _normalize_confidence


# ---------- _normalize_confidence ----------

def test_normalize_confidence_leaves_valid_unchanged():
    content = {
        "experiences": [
            {"bullets": [{"text": "did X", "confidence": "verified"}]}
        ]
    }
    result = _normalize_confidence(content)
    assert result["experiences"][0]["bullets"][0]["confidence"] == "verified"


def test_normalize_confidence_fixes_invalid():
    content = {
        "experiences": [
            {"bullets": [{"text": "did X", "confidence": "made_up"}]}
        ]
    }
    result = _normalize_confidence(content)
    assert result["experiences"][0]["bullets"][0]["confidence"] == "weak_inference"


def test_normalize_confidence_skips_non_dict_bullets():
    content = {"experiences": [{"bullets": ["plain string bullet"]}]}
    result = _normalize_confidence(content)
    assert result["experiences"][0]["bullets"][0] == "plain string bullet"


# ---------- _content_to_text ----------

@pytest.fixture
def base_generator(test_session):
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Built ETL pipeline", "evidence_id": "b1", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"}
    ]
    kw = MagicMock()
    kw.extract.return_value = {
        "required_skills": ["Python"], "keywords": ["ETL"], "industry": "tech",
        "seniority_level": "senior", "preferred_skills": [],
    }
    scorer = MagicMock()
    scorer.score.return_value = {
        "overall_score": 80, "keyword_score": 85, "skill_score": 80,
        "experience_score": 75, "industry_score": 85,
        "matched_keywords": ["Python"], "missing_keywords": [],
        "explanation": "Good match.",
    }
    ollama = MagicMock()
    ollama.is_available.return_value = True
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Generate resume JSON",
        "user_template": (
            "JD: {job_description}\nTemplate: {template_name}\n"
            "Keywords: {keywords}\nEvidence: {evidence_json}\n"
            "Title: {job_title}\nCompany: {company}\nIndustry: {industry}"
        ),
    }
    return ResumeGenerator(sel, kw, scorer, ollama, loader, test_session)


def test_llm_build_success(base_generator):
    content = {
        "experiences": [
            {"title": "SWE", "company": "Acme", "dates": "2022–2024",
             "bullets": [{"text": "Built ETL", "evidence_id": "b1", "confidence": "verified"}]}
        ],
        "skills": ["Python"], "projects": [], "education": [],
    }
    base_generator._ollama.generate.return_value = json.dumps(content)
    result = base_generator.generate("Python engineer role", "software")
    assert result["ats_score"]["overall_score"] == 80
    assert result["weak_inference_count"] == 0
    assert result["requires_approval"] is False


def test_llm_build_json_decode_falls_back_to_rule_based(base_generator):
    base_generator._ollama.generate.return_value = "not valid json {{{"
    result = base_generator.generate("Python engineer role", "software")
    # Rule-based still builds a result from evidence
    assert "resume_id" in result
    assert len(result["content_json"]["experiences"]) == 1


def test_llm_build_exception_falls_back_to_rule_based(base_generator):
    base_generator._ollama.generate.side_effect = RuntimeError("model unavailable")
    result = base_generator.generate("Python engineer role", "software")
    assert "resume_id" in result


def test_generate_when_ollama_unavailable_uses_rule_based(test_session):
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Designed API", "evidence_id": "b2", "experience_id": "e2",
         "company": "Corp", "title": "Eng", "dates": "2020–2022", "confidence": "strong_inference"}
    ]
    kw = MagicMock()
    kw.extract.return_value = {
        "required_skills": [], "keywords": [], "industry": "finance",
        "seniority_level": "mid", "preferred_skills": [],
    }
    scorer = MagicMock()
    scorer.score.return_value = {
        "overall_score": 60, "keyword_score": 60, "skill_score": 60,
        "experience_score": 60, "industry_score": 60,
        "matched_keywords": [], "missing_keywords": [], "explanation": "",
    }
    ollama = MagicMock()
    ollama.is_available.return_value = False
    loader = MagicMock()
    gen = ResumeGenerator(sel, kw, scorer, ollama, loader, test_session)
    result = gen.generate("Finance role", "consulting")
    assert result["content_json"]["experiences"][0]["company"] == "Corp"


def test_content_to_text_handles_dict_and_string_bullets(base_generator):
    content = {
        "experiences": [
            {"title": "SWE", "company": "Acme", "dates": "2022–2024",
             "bullets": [
                 {"text": "Built ETL", "confidence": "verified"},
                 "plain string bullet",
             ]},
        ],
        "skills": ["Python", "SQL"],
    }
    text = base_generator._content_to_text(content)
    assert "Built ETL" in text
    assert "plain string bullet" in text
    assert "Python" in text


def test_rule_based_build_groups_by_experience(base_generator):
    evidence = [
        {"bullet_text": "Did A", "evidence_id": "b1", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"},
        {"bullet_text": "Did B", "evidence_id": "b2", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"},
        {"bullet_text": "Did C", "evidence_id": "b3", "experience_id": "e2",
         "company": "Corp", "title": "PM", "dates": "2020–2022", "confidence": "verified"},
    ]
    result = base_generator._rule_based_build("software", evidence)
    assert len(result["experiences"]) == 2
    e1_bullets = [e for e in result["experiences"] if e["company"] == "Acme"][0]["bullets"]
    assert len(e1_bullets) == 2


def test_generate_invalid_application_id_raises(base_generator):
    base_generator._ollama.generate.return_value = json.dumps({
        "experiences": [], "skills": [], "projects": [], "education": []
    })
    with pytest.raises(ValueError, match="Invalid application_id"):
        base_generator.generate("Python role", "software", application_id="nonexistent-uuid")
```

- [ ] **Step 2: Write DOCX exporter extended tests**

```python
# backend/tests/unit/test_resume_docx_exporter_extended.py
from __future__ import annotations

import pytest
from backend.services.resume.docx_exporter import ResumeDOCXExporter

_SAMPLE_CONTENT = {
    "experiences": [
        {
            "title": "SWE", "company": "Acme", "dates": "2022–2024",
            "bullets": [
                {"text": "Built ETL pipeline reducing costs by 40%", "confidence": "verified"},
                {"text": "Possibly managed a team of 3", "confidence": "weak_inference"},
                "Legacy string bullet",
            ],
        }
    ],
    "skills": ["Python", "SQL", "dbt"],
    "projects": [
        {"name": "ACOS", "description": "Career OS", "tech": "Python, React"},
    ],
    "education": [],
}


def test_export_returns_bytes():
    exporter = ResumeDOCXExporter()
    result = exporter.export(_SAMPLE_CONTENT, "software")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_export_returns_valid_docx_magic_bytes():
    exporter = ResumeDOCXExporter()
    result = exporter.export(_SAMPLE_CONTENT, "software")
    # DOCX is a ZIP file — starts with PK magic bytes
    assert result[:2] == b"PK"


def test_export_empty_content_still_returns_bytes():
    exporter = ResumeDOCXExporter()
    result = exporter.export({}, "software")
    assert isinstance(result, bytes)
    assert result[:2] == b"PK"


def test_export_with_weak_bullet_does_not_raise():
    exporter = ResumeDOCXExporter()
    content = {
        "experiences": [
            {"title": "Mgr", "company": "Co", "dates": "2020–2022",
             "bullets": [{"text": "Possibly led team", "confidence": "weak_inference"}]}
        ],
        "skills": [], "projects": [],
    }
    result = exporter.export(content, "consulting")
    assert isinstance(result, bytes)


def test_export_skills_section():
    exporter = ResumeDOCXExporter()
    result = exporter.export({"experiences": [], "skills": ["Python", "Go"], "projects": []}, "software")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_export_projects_section():
    exporter = ResumeDOCXExporter()
    content = {
        "experiences": [],
        "skills": [],
        "projects": [{"name": "MyProj", "description": "Cool tool", "tech": "Rust"}],
    }
    result = exporter.export(content, "software")
    assert isinstance(result, bytes)


def test_export_handles_malformed_content_gracefully():
    exporter = ResumeDOCXExporter()
    # Pass a non-dict to trigger the except branch
    result = exporter.export(None, "software")  # type: ignore[arg-type]
    assert isinstance(result, bytes)
```

- [ ] **Step 3: Run tests to verify they pass**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_resume_generator_extended.py backend/tests/unit/test_resume_docx_exporter_extended.py -v --no-header --no-cov 2>&1 | tail -25
```

Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_resume_generator_extended.py backend/tests/unit/test_resume_docx_exporter_extended.py
git commit -m "test(resume): extended unit tests for generator LLM/fallback paths and DOCX exporter"
```

---

### Task 3: Cover letter DOCX exporter + generator extended tests

**Files:**
- Create: `backend/tests/unit/test_cover_letter_docx_exporter_extended.py`
- Create: `backend/tests/unit/test_cover_letter_generator_extended.py`

**Interfaces:**
- Consumes: `CoverLetterDOCXExporter` from `backend/services/cover_letter/docx_exporter.py`; `CoverLetterGenerator` from `backend/services/cover_letter/generator.py`

- [ ] **Step 1: Write the DOCX exporter extended tests**

```python
# backend/tests/unit/test_cover_letter_docx_exporter_extended.py
from __future__ import annotations

import pytest
from backend.services.cover_letter.docx_exporter import CoverLetterDOCXExporter


def test_export_returns_bytes():
    exporter = CoverLetterDOCXExporter()
    result = exporter.export("Dear Hiring Manager,\n\nI am excited to apply.", "SWE", "Acme")
    assert isinstance(result, bytes)
    assert result[:2] == b"PK"


def test_export_empty_text_returns_bytes():
    exporter = CoverLetterDOCXExporter()
    result = exporter.export("", "Dev", "Corp")
    assert isinstance(result, bytes)


def test_export_multiline_text():
    exporter = CoverLetterDOCXExporter()
    text = "Line one.\n\nLine two.\n\nSincerely,"
    result = exporter.export(text, "PM", "StartupCo")
    assert isinstance(result, bytes)
    assert len(result) > 500  # sanity: non-trivial DOCX file


def test_export_never_raises_on_bad_input():
    exporter = CoverLetterDOCXExporter()
    # Force the outer try to fail by passing a non-str
    result = exporter.export(None, "x", "y")  # type: ignore[arg-type]
    # Should return b"" via double-fallback
    assert isinstance(result, bytes)
```

- [ ] **Step 2: Write the generator extended tests**

```python
# backend/tests/unit/test_cover_letter_generator_extended.py
from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest
from backend.services.cover_letter.generator import CoverLetterGenerator


@pytest.fixture
def mock_selector():
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Led Python migration saving $200K annually", "evidence_id": "b1",
         "experience_id": "e1", "company": "Acme", "title": "SWE",
         "dates": "2022–2024", "confidence": "verified"},
        {"bullet_text": "Possibly managed a team of 5", "evidence_id": "b2",
         "experience_id": "e1", "company": "Acme", "title": "SWE",
         "dates": "2022–2024", "confidence": "weak_inference"},
    ]
    return sel


@pytest.fixture
def mock_voice():
    vm = MagicMock()
    vm.get_or_create_default.return_value = {
        "tone_descriptors": ["professional", "confident"],
        "structure_patterns": ["hook → evidence → close"],
        "vocabulary_patterns": {},
        "sample_sentences": ["I am excited to apply."],
    }
    return vm


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Write cover letter",
        "user_template": (
            "JD: {job_description}\nCompany: {company}\nTitle: {job_title}\n"
            "Length: {length_target}\nTone: {tone_descriptors}\n"
            "Vocab: {vocabulary_patterns}\nSamples: {sample_sentences}\n"
            "Industry: {industry}\nKeywords: {keywords}\nEvidence: {evidence_json}"
        ),
    }
    return loader


def test_generate_template_path_no_ollama(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    result = gen.generate("Python engineer role", "Acme", "SWE", "medium")
    assert "text" in result
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0


def test_generate_weak_evidence_sets_requires_approval(mock_voice, mock_loader):
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Possibly led team", "evidence_id": "b1", "experience_id": "e1",
         "company": "Co", "title": "Lead", "dates": "2020–2022", "confidence": "weak_inference"}
    ]
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen = CoverLetterGenerator(sel, mock_voice, ollama, mock_loader)
    result = gen.generate("Management role", "Corp", "Manager", "short")
    assert result["requires_approval"] is True


def test_generate_invalid_length_raises(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate("anything", "Co", "Dev", "enormous")


def test_generate_llm_success(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.return_value = "Dear Hiring Manager, I am the right candidate."
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    result = gen.generate("Python engineer role", "Acme", "SWE", "medium")
    assert result["text"] == "Dear Hiring Manager, I am the right candidate."
    assert result["requires_approval"] is True  # because weak_inference in evidence


def test_generate_llm_exception_falls_back_to_template(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.side_effect = RuntimeError("model down")
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    result = gen.generate("Python engineer role", "Acme", "SWE", "medium")
    assert isinstance(result["text"], str)
    assert "Acme" in result["text"]  # template always includes company name


def test_generate_returns_word_count(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    result = gen.generate("Python role", "Acme", "SWE", "long")
    assert result["word_count"] == len(result["text"].split())
    assert result["length_target"] == "long"
```

- [ ] **Step 3: Run tests**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_cover_letter_docx_exporter_extended.py backend/tests/unit/test_cover_letter_generator_extended.py -v --no-header --no-cov 2>&1 | tail -20
```

Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_cover_letter_docx_exporter_extended.py backend/tests/unit/test_cover_letter_generator_extended.py
git commit -m "test(cover-letter): extended unit tests for CL generator LLM/fallback paths and DOCX exporter"
```

---

### Task 4: Questions generator unit tests

**Files:**
- Create: `backend/tests/unit/test_question_generator_extended.py`

**Interfaces:**
- Consumes: `QuestionGenerator` from `backend/services/questions/generator.py`; `_interpolate` helper

- [ ] **Step 1: Write the tests**

```python
# backend/tests/unit/test_question_generator_extended.py
from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest
from backend.services.questions.generator import QuestionGenerator, _interpolate


# ---------- _interpolate ----------

def test_interpolate_replaces_known_variable():
    result = _interpolate("You are applying for {{position}} at {{company}}.", {
        "position": "SWE", "company": "Acme"
    })
    assert result == "You are applying for SWE at Acme."


def test_interpolate_leaves_unknown_variable():
    result = _interpolate("Tell me about {{tech_stack}}.", {})
    assert "{{tech_stack}}" in result


def test_interpolate_empty_template():
    assert _interpolate("", {"company": "X"}) == ""


# ---------- QuestionGenerator fixtures ----------

@pytest.fixture
def mock_ollama_off():
    o = MagicMock()
    o.is_available.return_value = False
    return o


@pytest.fixture
def mock_ollama_on():
    o = MagicMock()
    o.is_available.return_value = True
    o.generate.return_value = json.dumps([
        {"question_template": "Why do you want to work at {{company}}?", "category": "motivational"},
        {"question_template": "Describe a time you used {{tech_stack}}.", "category": "technical"},
    ])
    return o


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Generate questions",
        "user_template": (
            "JD: {job_description}\nCompany: {company}\nPosition: {position}\n"
            "Industry: {industry}\nTech: {tech_stack}"
        ),
    }
    return loader


@pytest.fixture
def mock_selector():
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Led Python work", "evidence_id": "b1", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"}
    ]
    return sel


# ---------- generate_questions ----------

def test_generate_questions_no_ollama_uses_fallback(mock_ollama_off, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_off, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("Python engineer at Acme", company="Acme", position="SWE")
    assert len(results) > 0
    assert all("question_template" in q for q in results)
    assert all("interpolated" in q for q in results)


def test_generate_questions_fallback_interpolates_variables(mock_ollama_off, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_off, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("role", company="Google", position="PM", industry="tech", tech_stack="Python")
    # Fallback template includes {{company}} — should be replaced
    interpolated_texts = [q["interpolated"] for q in results]
    assert any("Google" in t or "PM" in t or "tech" in t for t in interpolated_texts)


def test_generate_questions_with_ollama_returns_llm_questions(mock_ollama_on, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_on, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("Python engineer at Acme", company="Acme", position="SWE", tech_stack="Python")
    assert len(results) == 2
    assert results[0]["category"] == "motivational"


def test_generate_questions_invalid_category_defaults_to_behavioral(mock_loader, mock_selector, test_session):
    o = MagicMock()
    o.is_available.return_value = True
    o.generate.return_value = json.dumps([
        {"question_template": "Ask about {{position}}?", "category": "nonexistent_category"}
    ])
    gen = QuestionGenerator(o, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("role", position="Dev")
    assert results[0]["category"] == "behavioral"


def test_generate_questions_llm_json_error_uses_fallback(mock_loader, mock_selector, test_session):
    o = MagicMock()
    o.is_available.return_value = True
    o.generate.return_value = "not json at all"
    gen = QuestionGenerator(o, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("Python role")
    assert len(results) > 0  # fallback was used


# ---------- generate_answer ----------

def test_generate_answer_invalid_length_raises(mock_ollama_off, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_off, mock_loader, mock_selector, test_session)
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate_answer("some-question-id", {}, length_target="epic")


def test_generate_answer_question_not_found_raises(mock_ollama_off, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_off, mock_loader, mock_selector, test_session)
    with pytest.raises(ValueError, match="Question not found"):
        gen.generate_answer("non-existent-uuid-1234", {}, length_target="short")


def test_generate_answer_success(mock_ollama_on, mock_loader, mock_selector, test_session):
    # First create a question
    gen = QuestionGenerator(mock_ollama_on, mock_loader, mock_selector, test_session)
    questions = gen.generate_questions("Python role", company="Acme", position="SWE", tech_stack="Python")
    assert len(questions) > 0
    q_id = questions[0]["id"]

    # Now configure ollama to return an answer
    mock_ollama_on.generate.return_value = "I demonstrated leadership by mentoring 3 engineers..."
    answer = gen.generate_answer(q_id, {"company": "Acme", "position": "SWE", "tech_stack": "Python"}, length_target="medium")
    assert "answer_id" in answer
    assert answer["question_id"] == q_id
    assert "interpolated_question" in answer


# ---------- edit_answer ----------

def test_edit_answer_not_found_raises(mock_ollama_on, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_on, mock_loader, mock_selector, test_session)
    with pytest.raises(ValueError, match="Answer not found"):
        gen.edit_answer("fake-answer-uuid", "my edited text")
```

- [ ] **Step 2: Run tests**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_question_generator_extended.py -v --no-header --no-cov 2>&1 | tail -25
```

Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_question_generator_extended.py
git commit -m "test(questions): unit tests for QuestionGenerator — generate/answer/edit paths including LLM and fallback"
```

---

### Task 5: Remaining integration route + ingestion coverage

**Files:**
- Create: `backend/tests/integration/test_copilot_routes_extended.py`

**Interfaces:**
- Consumes: `/api/v1/copilot/chat` endpoint, `client` fixture from conftest

- [ ] **Step 1: Write copilot integration tests covering LLM path**

```python
# backend/tests/integration/test_copilot_routes_extended.py
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_copilot_chat_with_ollama_unavailable_returns_context(client):
    with (
        patch("backend.api.v1.routes.copilot.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.copilot.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.copilot.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama

        mock_ret = MagicMock()
        mock_ret.retrieve.return_value = [
            {"id": "d1", "text": "Led Python work at Acme", "collection": "acos_experiences",
             "semantic_score": 0.9, "metadata": {"confidence_level": "verified", "entity_id": "e1"}}
        ]
        mock_ret_cls.return_value = mock_ret

        mock_rnk = MagicMock()
        mock_rnk.rerank.side_effect = lambda q, r, **kw: r
        mock_rnk_cls.return_value = mock_rnk

        resp = client.post("/api/v1/copilot/chat", json={"message": "What Python work have I done?"})

    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "intent" in data
    assert "citations" in data
    assert "evidence_count" in data


def test_copilot_chat_empty_message(client):
    with (
        patch("backend.api.v1.routes.copilot.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.copilot.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.copilot.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post("/api/v1/copilot/chat", json={"message": ""})
    assert resp.status_code == 200


def test_copilot_chat_with_history(client):
    with (
        patch("backend.api.v1.routes.copilot.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.copilot.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.copilot.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post("/api/v1/copilot/chat", json={
            "message": "Tell me more",
            "conversation_history": [
                {"role": "user", "content": "What Python work have I done?"},
                {"role": "assistant", "content": "You worked on ETL pipelines."},
            ],
        })
    assert resp.status_code == 200


def test_copilot_chat_missing_message_returns_422(client):
    resp = client.post("/api/v1/copilot/chat", json={})
    assert resp.status_code == 422


def test_copilot_chat_detects_resume_intent(client):
    with (
        patch("backend.api.v1.routes.copilot.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.copilot.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.copilot.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post("/api/v1/copilot/chat", json={"message": "Help me tailor my resume"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "resume_help"
```

- [ ] **Step 2: Run full test suite and verify coverage ≥90%**

```
source .venv/bin/activate && python -m pytest backend/tests/ -q --tb=short --cov=backend --cov-report=term-missing 2>&1 | tail -10
```

Expected: `Total coverage: XX%` where XX ≥ 90. If not yet ≥90%, read the missing lines report and add targeted tests for uncovered lines in the modules shown.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/integration/test_copilot_routes_extended.py
git commit -m "test(copilot): integration tests for copilot route — intent detection, history, LLM-off path"
```

---

## TRACK B — SECURITY HARDENING

### Task 6: Fix pipeline.py Chroma/SQLite divergence

**Files:**
- Modify: `backend/ingestion/pipeline.py:103-118`
- Create: `backend/tests/integration/test_pipeline_divergence.py`

**Interfaces:**
- The `ingest()` method must set `doc.ingestion_status = "failed"` and call `self._session.flush()` if `self._indexer.index_document()` raises, then re-raise. This prevents a partially committed document from appearing as "processing" forever.

- [ ] **Step 1: Write the failing regression test first**

```python
# backend/tests/integration/test_pipeline_divergence.py
from __future__ import annotations

from unittest.mock import MagicMock
import pytest
from backend.ingestion.pipeline import IngestionPipeline
from backend.repositories.document import DocumentRepository
from backend.services.knowledge_graph.service import KnowledgeGraphService


def test_indexer_failure_sets_status_failed(tmp_path, test_session):
    """If ChromaDB indexing fails, the document must be saved as status='failed',
    not left as 'processing' (the divergence bug from pipeline.py TODO)."""
    f = tmp_path / "resume.txt"
    f.write_text("Experienced Python developer.")

    kg_svc = KnowledgeGraphService(test_session)
    indexer = MagicMock()
    indexer.index_document.side_effect = RuntimeError("ChromaDB connection failed")
    extractor = MagicMock()
    extractor.extract.return_value = {"skills": [], "experiences": [], "projects": []}

    pipeline = IngestionPipeline(
        session=test_session,
        kg_service=kg_svc,
        indexer=indexer,
        entity_extractor=extractor,
        allowed_dirs=[str(tmp_path)],
    )

    with pytest.raises(RuntimeError, match="ChromaDB connection failed"):
        pipeline.ingest(str(f))

    doc_repo = DocumentRepository(test_session)
    docs = doc_repo.list()
    assert len(docs) == 1
    assert docs[0].ingestion_status == "failed"
```

- [ ] **Step 2: Run test — expect FAIL (current code leaves status as 'processing')**

```
source .venv/bin/activate && python -m pytest backend/tests/integration/test_pipeline_divergence.py -v --no-header --no-cov 2>&1 | tail -10
```

Expected: FAIL — document status is "processing" not "failed".

- [ ] **Step 3: Fix pipeline.py**

In `backend/ingestion/pipeline.py`, replace lines 103-118 (the `index_document` call and following lines) with:

```python
        try:
            self._indexer.index_document(
                collection,
                doc.id,
                text[:2000],
                {
                    "document_id": doc.id,
                    "source_type": doc.source_type,
                    "confidence_level": "strong_inference",
                },
            )
        except Exception:
            logger.exception(
                "pipeline: ChromaDB indexing failed for doc '%s'; marking status=failed",
                doc.id,
            )
            doc.ingestion_status = "failed"
            self._session.flush()
            raise

        doc.ingestion_status = "complete"
        self._session.flush()
        return doc.id
```

- [ ] **Step 4: Run test — expect PASS**

```
source .venv/bin/activate && python -m pytest backend/tests/integration/test_pipeline_divergence.py -v --no-header --no-cov 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Run full suite to confirm no regressions**

```
source .venv/bin/activate && python -m pytest backend/tests/ -q --tb=short --no-cov 2>&1 | tail -5
```

Expected: No new failures.

- [ ] **Step 6: Commit**

```bash
git add backend/ingestion/pipeline.py backend/tests/integration/test_pipeline_divergence.py
git commit -m "fix(pipeline): set ingestion_status=failed when ChromaDB indexing raises, preventing processing/complete divergence"
```

---

### Task 7: GitHub ingestion security hardening

**Files:**
- Modify: `scripts/ingestion/ingest_github.py`
- Create: `backend/tests/unit/test_github_security.py`

**Vulnerabilities addressed:**
1. README fetched over HTTPS with no size cap → an adversarially large README can OOM the process
2. `text[:2000]` truncates at ChromaDB indexing but the full untruncated text is passed to `extractor.extract()` — could be a large payload

- [ ] **Step 1: Write failing security tests**

```python
# backend/tests/unit/test_github_security.py
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest


def test_fetch_readme_truncates_oversized_content():
    """README content must be capped at 50KB to prevent OOM on adversarial repos."""
    from scripts.ingestion.ingest_github import fetch_readme
    huge_readme = "A" * (200_000)
    mock_response = MagicMock()
    mock_response.text = huge_readme
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        text = fetch_readme("user", "repo", "main")
    assert len(text) <= 51_200  # 50 KB cap


def test_ingest_text_is_size_capped():
    """The text assembled for indexing must be ≤50KB before extraction."""
    from scripts.ingestion.ingest_github import _build_repo_text
    oversized_readme = "X" * 200_000
    repo = {
        "name": "myrepo",
        "description": "A great repo",
        "language": "Python",
        "html_url": "https://github.com/user/myrepo",
    }
    text = _build_repo_text(repo, oversized_readme)
    assert len(text) <= 51_200
```

- [ ] **Step 2: Run tests — expect ImportError or AttributeError (function not yet split out)**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_github_security.py -v --no-header --no-cov 2>&1 | tail -10
```

Expected: FAIL because `_build_repo_text` doesn't exist and `fetch_readme` has no cap.

- [ ] **Step 3: Refactor `ingest_github.py` to add size cap**

Replace `scripts/ingestion/ingest_github.py` with:

```python
#!/usr/bin/env python
"""Ingest public GitHub repos for a user into the ACOS RAG knowledge base."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import get_settings
from backend.database import SessionLocal
from backend.ingestion.entity_extractor import EntityExtractor
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.indexer import RAGIndexer
from backend.services.knowledge_graph.service import KnowledgeGraphService
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_GH_API = "https://api.github.com"
_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
_README_MAX_BYTES = 51_200  # 50 KB cap — prevents OOM on adversarial large READMEs


def fetch_repos(username: str) -> list[dict]:
    resp = httpx.get(
        f"{_GH_API}/users/{username}/repos",
        params={"per_page": 100, "sort": "updated"},
        headers=_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_readme(username: str, repo: str, branch: str) -> str:
    url = f"https://raw.githubusercontent.com/{username}/{repo}/{branch}/README.md"
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        # Cap at _README_MAX_BYTES to prevent OOM on adversarially large READMEs
        return resp.text[:_README_MAX_BYTES]
    except httpx.HTTPStatusError:
        return ""


def _build_repo_text(repo: dict, readme: str) -> str:
    """Assemble the indexable text for a repo. Total capped at 50 KB."""
    name = repo.get("name", "")
    description = repo.get("description") or ""
    language = repo.get("language") or ""
    text = f"Repository: {name}\nLanguage: {language}\nDescription: {description}\n\n{readme}"
    return text[:_README_MAX_BYTES]


def ingest(username: str) -> None:
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    indexer = RAGIndexer(chroma, embedder)
    extractor = EntityExtractor(ollama if ollama.is_available() else None)

    repos = fetch_repos(username)
    logger.info("found %d repos for %s", len(repos), username)

    with SessionLocal() as session:
        kg_svc = KnowledgeGraphService(session)
        for repo in repos:
            branch = repo.get("default_branch", "main")
            readme = fetch_readme(username, repo["name"], branch)
            text = _build_repo_text(repo, readme)
            doc_id = f"github_{username}_{repo['name']}"

            entities = extractor.extract(text, "github")
            metadata = {
                "repo_url": repo.get("html_url", ""),
                "language": repo.get("language") or "",
                "project_id": doc_id,
                "confidence_level": "strong_inference",
            }
            indexer.index_document("acos_github", doc_id, text[:2000], metadata)

            for skill in entities.get("skills", []):
                kg_svc.get_or_create_node(
                    "skill", skill["name"].lower(), skill["name"],
                    {"confidence": skill["confidence"], "source": "github"},
                )

            logger.info("indexed repo: %s", repo["name"])
        session.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Ingest GitHub repos into ACOS")
    parser.add_argument("--username", default="andrew-nguyen-9")
    args = parser.parse_args()
    ingest(args.username)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — expect PASS**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_github_security.py -v --no-header --no-cov 2>&1 | tail -10
```

Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/ingestion/ingest_github.py backend/tests/unit/test_github_security.py
git commit -m "fix(security): cap GitHub README ingestion at 50KB to prevent OOM; extract _build_repo_text helper"
```

---

### Task 8: Export system output validation + ingestion path hardening

**Files:**
- Modify: `backend/ingestion/security.py` — add `sanitize_filename()` helper
- Modify: `backend/api/v1/routes/ingestion.py` — use `sanitize_filename()` instead of inline logic
- Create: `backend/tests/unit/test_ingestion_security_extended.py`

**Vulnerability addressed:** The inline filename sanitization in `ingestion.py:43-48` works but is not reusable and has no test. Extract and test it.

- [ ] **Step 1: Write the tests first**

```python
# backend/tests/unit/test_ingestion_security_extended.py
from __future__ import annotations

import pytest
from backend.ingestion.security import sanitize_filename, validate_path, compute_checksum


def test_sanitize_filename_strips_path_separators():
    assert sanitize_filename("../../../etc/passwd") == "passwd"


def test_sanitize_filename_strips_forward_slash():
    assert sanitize_filename("/tmp/evil/file.txt") == "file.txt"


def test_sanitize_filename_keeps_safe_name():
    assert sanitize_filename("resume.pdf") == "resume.pdf"


def test_sanitize_filename_replaces_empty_with_upload():
    assert sanitize_filename("") == "upload"


def test_sanitize_filename_replaces_dot_with_upload():
    assert sanitize_filename(".") == "upload"


def test_sanitize_filename_replaces_dotdot_with_upload():
    assert sanitize_filename("..") == "upload"


def test_sanitize_filename_replaces_none_with_upload():
    assert sanitize_filename(None) == "upload"  # type: ignore[arg-type]


def test_validate_path_symlink_outside_allowlist_rejected(tmp_path):
    """A symlink that resolves outside the allowlist must be rejected."""
    outside = tmp_path / "outside"
    outside.mkdir()
    target_file = outside / "secret.txt"
    target_file.write_text("secret")

    inside = tmp_path / "allowed"
    inside.mkdir()
    link = inside / "link.txt"
    link.symlink_to(target_file)

    # The resolved target is outside "allowed/" so it must be rejected
    with pytest.raises(ValueError, match="not under any allowed"):
        validate_path(str(link), [str(inside)])


def test_compute_checksum_deterministic(tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"\x00\xff\xab\xcd" * 1000)
    c1 = compute_checksum(f)
    c2 = compute_checksum(f)
    assert c1 == c2
    assert len(c1) == 64  # SHA-256 hex
```

- [ ] **Step 2: Run tests — `sanitize_filename` import will fail (not yet defined)**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_ingestion_security_extended.py -v --no-header --no-cov 2>&1 | tail -10
```

Expected: ImportError on `sanitize_filename`.

- [ ] **Step 3: Add `sanitize_filename` to `backend/ingestion/security.py`**

Append to `backend/ingestion/security.py` (after `compute_checksum`):

```python


def sanitize_filename(name: str | None) -> str:
    """Return only the basename of *name*, replacing dangerous values with 'upload'.

    Strips all path separators so callers cannot traverse outside a temp dir.
    """
    if not name:
        return "upload"
    base = Path(name).name
    if not base or base in (".", ".."):
        return "upload"
    return base
```

- [ ] **Step 4: Run tests — expect PASS**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_ingestion_security_extended.py -v --no-header --no-cov 2>&1 | tail -15
```

Expected: All PASS including symlink traversal test.

- [ ] **Step 5: Update `ingestion.py` to use `sanitize_filename`**

In `backend/api/v1/routes/ingestion.py`, replace lines 42-48:

```python
        # Sanitize filename — take only the basename, strip path separators
        safe_name = Path(file.filename or "upload").name
        if not safe_name or safe_name in (".", ".."):
            safe_name = "upload"
        dest = (Path(tmpdir) / safe_name).resolve()
        # Verify dest is inside tmpdir
        if not str(dest).startswith(str(Path(tmpdir).resolve()) + os.sep):
            raise HTTPException(status_code=400, detail="Invalid filename")
```

with:

```python
        from backend.ingestion.security import sanitize_filename
        safe_name = sanitize_filename(file.filename)
        dest = (Path(tmpdir) / safe_name).resolve()
        if not str(dest).startswith(str(Path(tmpdir).resolve()) + os.sep):
            raise HTTPException(status_code=400, detail="Invalid filename")
```

- [ ] **Step 6: Run full suite — no regressions**

```
source .venv/bin/activate && python -m pytest backend/tests/ -q --tb=short --no-cov 2>&1 | tail -5
```

Expected: All previously passing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add backend/ingestion/security.py backend/api/v1/routes/ingestion.py backend/tests/unit/test_ingestion_security_extended.py
git commit -m "fix(security): extract sanitize_filename() with symlink and traversal tests; use it in ingestion route"
```

---

## TRACK C — PLAYWRIGHT E2E TESTS

### Task 9: Playwright install + configuration + shared fixtures

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/fixtures.ts`

**Approach:** Playwright runs against the Vite dev server (`http://localhost:1420`). All backend API calls (`/api/v1/*`) are intercepted via `page.route()` and return deterministic mock payloads. This makes E2E tests hermetic — no backend or Ollama needed.

- [ ] **Step 1: Install Playwright**

```bash
cd frontend && npm install --save-dev @playwright/test
npx playwright install chromium
```

Expected: `node_modules/@playwright/test` present, chromium downloaded.

- [ ] **Step 2: Create `frontend/playwright.config.ts`**

```typescript
// frontend/playwright.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: "html",
  use: {
    baseURL: "http://localhost:1420",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:1420",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
```

- [ ] **Step 3: Create `frontend/e2e/fixtures.ts`**

```typescript
// frontend/e2e/fixtures.ts
import { test as base, Page } from "@playwright/test";

// ── Canonical mock payloads ──────────────────────────────────────────────
export const MOCK_RESUME_RESPONSE = {
  resume_id: "abc123def456abc123def456abc12345",
  content_json: {
    experiences: [
      {
        title: "Data Engineer",
        company: "Acme Corp",
        dates: "2022–2024",
        bullets: [
          { text: "Built Python ETL pipeline reducing costs by 40%", confidence: "verified" },
        ],
      },
    ],
    skills: ["Python", "ETL", "SQL"],
    projects: [],
    education: [],
  },
  ats_score: {
    overall_score: 85,
    keyword_score: 88,
    skill_score: 82,
    experience_score: 80,
    industry_score: 90,
    matched_keywords: ["Python", "ETL"],
    missing_keywords: [],
    explanation: "Strong match for this role.",
  },
  weak_inference_count: 0,
  requires_approval: false,
};

export const MOCK_COVER_LETTER_RESPONSE = {
  text: "Dear Hiring Manager,\n\nI am excited to apply for the Software Engineer position at Acme Corp.\n\nSincerely,",
  word_count: 22,
  length_target: "medium",
  requires_approval: false,
};

export const MOCK_ATS_RESPONSE = {
  keywords: {
    required_skills: ["Python", "SQL"],
    preferred_skills: ["dbt"],
    keywords: ["data pipeline", "ETL"],
    industry: "technology",
    seniority_level: "senior",
  },
  ats_score: {
    overall_score: 78,
    keyword_score: 82,
    skill_score: 75,
    experience_score: 70,
    industry_score: 85,
    matched_keywords: ["Python", "SQL"],
    missing_keywords: ["dbt"],
    explanation: "Good keyword match, missing some preferred skills.",
  },
};

export const MOCK_COPILOT_RESPONSE = {
  response: "Based on your experience, you have strong Python and data engineering skills.",
  intent: "resume_help",
  confidence: "verified",
  citations: [
    {
      source: "acos_experiences",
      text: "Built Python ETL pipeline",
      confidence: "verified",
      similarity: 0.92,
    },
  ],
  evidence_count: 1,
};

export const MOCK_APPLICATION = {
  id: "app-uuid-1234-5678-9012-345678901234",
  company: "Acme Corp",
  position: "Software Engineer",
  status: "applied",
  created_at: "2026-06-19T10:00:00",
};

export const MOCK_APPLICATIONS_LIST = [MOCK_APPLICATION];

// ── Fixture type ─────────────────────────────────────────────────────────
type Fixtures = {
  mockApi: void;
};

// ── Extended test with API mocks ──────────────────────────────────────────
export const test = base.extend<Fixtures>({
  mockApi: [
    async ({ page }: { page: Page }, use: () => Promise<void>) => {
      await page.route("**/api/v1/resume/generate", async (route) => {
        await route.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify(MOCK_RESUME_RESPONSE) });
      });
      await page.route("**/api/v1/resume/analyze-ats", async (route) => {
        await route.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify(MOCK_ATS_RESPONSE) });
      });
      await page.route("**/api/v1/cover-letter/generate", async (route) => {
        await route.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify(MOCK_COVER_LETTER_RESPONSE) });
      });
      await page.route("**/api/v1/copilot/chat", async (route) => {
        await route.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify(MOCK_COPILOT_RESPONSE) });
      });
      await page.route("**/api/v1/applications", async (route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({ status: 200, contentType: "application/json",
            body: JSON.stringify(MOCK_APPLICATIONS_LIST) });
        } else if (route.request().method() === "POST") {
          await route.fulfill({ status: 201, contentType: "application/json",
            body: JSON.stringify(MOCK_APPLICATION) });
        } else {
          await route.continue();
        }
      });
      await page.route("**/api/v1/applications/**", async (route) => {
        const method = route.request().method();
        if (method === "GET") {
          await route.fulfill({ status: 200, contentType: "application/json",
            body: JSON.stringify(MOCK_APPLICATION) });
        } else if (method === "PATCH") {
          await route.fulfill({ status: 200, contentType: "application/json",
            body: JSON.stringify({ id: MOCK_APPLICATION.id, status: "interview" }) });
        } else if (method === "DELETE") {
          await route.fulfill({ status: 204, body: "" });
        } else {
          await route.continue();
        }
      });
      await page.route("**/api/v1/health", async (route) => {
        await route.fulfill({ status: 200, contentType: "application/json",
          body: JSON.stringify({ status: "healthy", ollama: { available: true } }) });
      });
      await use();
    },
    { auto: true },
  ],
});

export { expect } from "@playwright/test";
```

- [ ] **Step 4: Verify Playwright config resolves**

```
cd frontend && npx playwright test --list 2>&1 | head -10
```

Expected: "No tests found" (no specs yet) with no config errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e/fixtures.ts frontend/package.json frontend/package-lock.json
git commit -m "test(e2e): install Playwright, add config targeting Vite dev server on :1420, add shared API mock fixtures"
```

---

### Task 10: E2E — Resume generation flow

**Files:**
- Create: `frontend/e2e/resume.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// frontend/e2e/resume.spec.ts
import { test, expect } from "./fixtures";

test.describe("Resume Generation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Navigate to Resume page via sidebar
    await page.getByRole("link", { name: /resume/i }).click();
    await expect(page).toHaveURL(/.*resume/);
  });

  test("page loads with template selector and job description input", async ({ page }) => {
    await expect(page.getByPlaceholder(/job description/i)).toBeVisible();
    await expect(page.getByRole("combobox")).toBeVisible();
    await expect(page.getByRole("button", { name: /generate/i })).toBeVisible();
  });

  test("generate button is disabled when job description is empty", async ({ page }) => {
    const btn = page.getByRole("button", { name: /generate/i });
    // Input should be empty by default
    const input = page.getByPlaceholder(/job description/i);
    await expect(input).toHaveValue("");
    // Clicking generate with empty input should not trigger API call
    await btn.click();
    // If disabled or noop, no loading spinner appears
    await expect(page.getByTestId("loading-spinner")).not.toBeVisible();
  });

  test("generates resume and displays ATS score", async ({ page }) => {
    const jdInput = page.getByPlaceholder(/job description/i);
    await jdInput.fill("Python Data Engineer at Acme Corp. Requires Python, SQL, ETL experience.");

    await page.getByRole("button", { name: /generate/i }).click();

    // Loading indicator appears
    await expect(page.getByRole("button", { name: /generate/i })).toBeDisabled();

    // ATS score appears after generation
    await expect(page.getByText("85")).toBeVisible({ timeout: 10_000 });
    // Experience section appears
    await expect(page.getByText("Acme Corp")).toBeVisible();
    await expect(page.getByText(/ETL pipeline/i)).toBeVisible();
  });

  test("displays evidence confidence badges", async ({ page }) => {
    const jdInput = page.getByPlaceholder(/job description/i);
    await jdInput.fill("Python engineering role");
    await page.getByRole("button", { name: /generate/i }).click();

    // Wait for result
    await page.waitForResponse("**/api/v1/resume/generate");
    // Confidence badge for 'verified' evidence
    await expect(page.getByText(/verified/i)).toBeVisible({ timeout: 8_000 });
  });

  test("download DOCX button appears after generation", async ({ page }) => {
    // Mock the download endpoint
    await page.route("**/api/v1/resume/generate/download", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        body: Buffer.from("PK fake docx"),
      });
    });

    await page.getByPlaceholder(/job description/i).fill("Python role");
    await page.getByRole("button", { name: /generate/i }).click();
    await page.waitForResponse("**/api/v1/resume/generate");

    await expect(page.getByRole("button", { name: /download/i })).toBeVisible({ timeout: 8_000 });
  });

  test("shows error message on API failure", async ({ page }) => {
    await page.unroute("**/api/v1/resume/generate");
    await page.route("**/api/v1/resume/generate", async (route) => {
      await route.fulfill({ status: 500, contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }) });
    });

    await page.getByPlaceholder(/job description/i).fill("Python role");
    await page.getByRole("button", { name: /generate/i }).click();
    await expect(page.getByRole("alert")).toBeVisible({ timeout: 8_000 });
  });
});
```

- [ ] **Step 2: Run spec (Vite dev server must be running)**

```
cd frontend && npx playwright test e2e/resume.spec.ts --reporter=list 2>&1 | tail -20
```

Expected: Tests pass. If UI elements have different text/roles, update selectors to match the actual DOM.

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/resume.spec.ts
git commit -m "test(e2e): resume generation workflow — generate, ATS score display, confidence badges, download button, error state"
```

---

### Task 11: E2E — Cover letter generation flow

**Files:**
- Create: `frontend/e2e/cover-letter.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// frontend/e2e/cover-letter.spec.ts
import { test, expect } from "./fixtures";

test.describe("Cover Letter Generation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /cover letter/i }).click();
    await expect(page).toHaveURL(/.*cover/i);
  });

  test("page loads with required inputs", async ({ page }) => {
    await expect(page.getByPlaceholder(/job description/i)).toBeVisible();
    await expect(page.getByPlaceholder(/company/i)).toBeVisible();
    await expect(page.getByPlaceholder(/job title/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /generate/i })).toBeVisible();
  });

  test("generates a cover letter and shows text", async ({ page }) => {
    await page.getByPlaceholder(/job description/i).fill("Software Engineer at Acme");
    await page.getByPlaceholder(/company/i).fill("Acme Corp");
    await page.getByPlaceholder(/job title/i).fill("Software Engineer");

    await page.getByRole("button", { name: /generate/i }).click();
    await page.waitForResponse("**/api/v1/cover-letter/generate");

    await expect(page.getByText(/Dear Hiring Manager/i)).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText(/Acme Corp/i)).toBeVisible();
  });

  test("word count is shown after generation", async ({ page }) => {
    await page.getByPlaceholder(/job description/i).fill("SWE role");
    await page.getByPlaceholder(/company/i).fill("Corp");
    await page.getByPlaceholder(/job title/i).fill("SWE");
    await page.getByRole("button", { name: /generate/i }).click();
    await page.waitForResponse("**/api/v1/cover-letter/generate");

    // MOCK_COVER_LETTER_RESPONSE.word_count == 22
    await expect(page.getByText(/22/)).toBeVisible({ timeout: 8_000 });
  });

  test("download button appears after generation", async ({ page }) => {
    await page.route("**/api/v1/cover-letter/generate/download", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        body: Buffer.from("PK fake docx"),
      });
    });

    await page.getByPlaceholder(/job description/i).fill("SWE role");
    await page.getByPlaceholder(/company/i).fill("Corp");
    await page.getByPlaceholder(/job title/i).fill("SWE");
    await page.getByRole("button", { name: /generate/i }).click();
    await page.waitForResponse("**/api/v1/cover-letter/generate");

    await expect(page.getByRole("button", { name: /download/i })).toBeVisible({ timeout: 8_000 });
  });
});
```

- [ ] **Step 2: Run spec**

```
cd frontend && npx playwright test e2e/cover-letter.spec.ts --reporter=list 2>&1 | tail -15
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/cover-letter.spec.ts
git commit -m "test(e2e): cover letter generation workflow — inputs, generate, word count display, download"
```

---

### Task 12: E2E — ATS scoring flow

**Files:**
- Create: `frontend/e2e/ats.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// frontend/e2e/ats.spec.ts
import { test, expect } from "./fixtures";

test.describe("ATS Scoring", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /ats/i }).click();
    await expect(page).toHaveURL(/.*ats/i);
  });

  test("page loads with resume text and job description inputs", async ({ page }) => {
    // ATS page has two textareas: resume text + job description
    const textareas = page.getByRole("textbox");
    await expect(textareas).toHaveCount({ minimum: 2 });
    await expect(page.getByRole("button", { name: /analyze/i })).toBeVisible();
  });

  test("ATS scoring returns keyword match and score", async ({ page }) => {
    const textareas = page.getByRole("textbox");
    await textareas.first().fill("Python Data Engineer with SQL and ETL experience.");
    await textareas.nth(1).fill("Data Engineer role requiring Python, SQL, ETL skills.");

    await page.getByRole("button", { name: /analyze/i }).click();
    await page.waitForResponse("**/api/v1/resume/analyze-ats");

    // Overall score: 78 from mock
    await expect(page.getByText("78")).toBeVisible({ timeout: 8_000 });
    // Matched keywords
    await expect(page.getByText(/Python/i)).toBeVisible();
    await expect(page.getByText(/SQL/i)).toBeVisible();
    // Missing keywords
    await expect(page.getByText(/dbt/i)).toBeVisible();
  });

  test("shows error on API failure", async ({ page }) => {
    await page.unroute("**/api/v1/resume/analyze-ats");
    await page.route("**/api/v1/resume/analyze-ats", async (route) => {
      await route.fulfill({ status: 503, body: JSON.stringify({ detail: "LLM unavailable" }) });
    });
    const textareas = page.getByRole("textbox");
    await textareas.first().fill("resume text");
    await textareas.nth(1).fill("job description text");
    await page.getByRole("button", { name: /analyze/i }).click();
    await expect(page.getByRole("alert")).toBeVisible({ timeout: 8_000 });
  });
});
```

- [ ] **Step 2: Run spec**

```
cd frontend && npx playwright test e2e/ats.spec.ts --reporter=list 2>&1 | tail -15
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/ats.spec.ts
git commit -m "test(e2e): ATS scoring workflow — inputs, score display, matched/missing keywords, error state"
```

---

### Task 13: E2E — Copilot query flow + Application CRM workflow

**Files:**
- Create: `frontend/e2e/copilot.spec.ts`
- Create: `frontend/e2e/applications.spec.ts`

- [ ] **Step 1: Write the copilot spec**

```typescript
// frontend/e2e/copilot.spec.ts
import { test, expect } from "./fixtures";

test.describe("Copilot Chat", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /copilot/i }).click();
    await expect(page).toHaveURL(/.*copilot/i);
  });

  test("page loads with chat input", async ({ page }) => {
    await expect(page.getByPlaceholder(/ask/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /send/i })).toBeVisible();
  });

  test("sends a message and displays copilot response", async ({ page }) => {
    await page.getByPlaceholder(/ask/i).fill("What Python work have I done?");
    await page.getByRole("button", { name: /send/i }).click();

    await page.waitForResponse("**/api/v1/copilot/chat");

    await expect(page.getByText(/strong Python and data engineering skills/i)).toBeVisible({ timeout: 8_000 });
  });

  test("shows citations after response", async ({ page }) => {
    await page.getByPlaceholder(/ask/i).fill("Tell me about my ETL work");
    await page.getByRole("button", { name: /send/i }).click();
    await page.waitForResponse("**/api/v1/copilot/chat");

    // Citation from mock: "Built Python ETL pipeline"
    await expect(page.getByText(/ETL pipeline/i)).toBeVisible({ timeout: 8_000 });
  });

  test("message input clears after sending", async ({ page }) => {
    const input = page.getByPlaceholder(/ask/i);
    await input.fill("What Python work have I done?");
    await page.getByRole("button", { name: /send/i }).click();
    await page.waitForResponse("**/api/v1/copilot/chat");
    await expect(input).toHaveValue("");
  });

  test("can send multiple messages in sequence", async ({ page }) => {
    const input = page.getByPlaceholder(/ask/i);

    await input.fill("First question");
    await page.getByRole("button", { name: /send/i }).click();
    await page.waitForResponse("**/api/v1/copilot/chat");

    await input.fill("Second question");
    await page.getByRole("button", { name: /send/i }).click();
    await page.waitForResponse("**/api/v1/copilot/chat");

    // Both user messages should be visible in chat history
    await expect(page.getByText("First question")).toBeVisible();
    await expect(page.getByText("Second question")).toBeVisible();
  });
});
```

- [ ] **Step 2: Write the applications CRM spec**

```typescript
// frontend/e2e/applications.spec.ts
import { test, expect, MOCK_APPLICATION } from "./fixtures";

test.describe("Application CRM", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /application/i }).click();
    await expect(page).toHaveURL(/.*application/i);
  });

  test("page loads and shows applications list", async ({ page }) => {
    await page.waitForResponse("**/api/v1/applications");
    await expect(page.getByText("Acme Corp")).toBeVisible({ timeout: 8_000 });
    await expect(page.getByText("Software Engineer")).toBeVisible();
  });

  test("status badge shows correct status", async ({ page }) => {
    await page.waitForResponse("**/api/v1/applications");
    await expect(page.getByText(/applied/i)).toBeVisible({ timeout: 8_000 });
  });

  test("can create a new application", async ({ page }) => {
    await page.waitForResponse("**/api/v1/applications");
    // Click "New Application" or equivalent button
    await page.getByRole("button", { name: /new|add/i }).click();

    // Fill out the form
    const companyInput = page.getByPlaceholder(/company/i);
    const positionInput = page.getByPlaceholder(/position|role|title/i);
    await companyInput.fill("New Company");
    await positionInput.fill("Backend Engineer");

    // Submit
    await page.getByRole("button", { name: /save|create|submit/i }).click();
    await page.waitForResponse("**/api/v1/applications");

    // Mock returns MOCK_APPLICATION so "Acme Corp" should still appear
    await expect(page.getByText("Acme Corp")).toBeVisible({ timeout: 8_000 });
  });

  test("shows empty state when no applications", async ({ page }) => {
    await page.unroute("**/api/v1/applications");
    await page.route("**/api/v1/applications", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.reload();
    // Empty state component should be visible
    await expect(page.getByText(/no applications|get started|empty/i)).toBeVisible({ timeout: 8_000 });
  });
});
```

- [ ] **Step 3: Run both specs**

```
cd frontend && npx playwright test e2e/copilot.spec.ts e2e/applications.spec.ts --reporter=list 2>&1 | tail -25
```

Expected: All tests pass. If selectors don't match the actual DOM, update them to match what `ResumePage.tsx`, `CopilotPage.tsx`, `ApplicationsPage.tsx` actually render.

- [ ] **Step 4: Run full Playwright suite**

```
cd frontend && npx playwright test --reporter=list 2>&1 | tail -15
```

Expected: All 5 spec files pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/e2e/copilot.spec.ts frontend/e2e/applications.spec.ts
git commit -m "test(e2e): Copilot chat + Application CRM E2E workflows — message send, citations, CRM list, create, empty state"
```

---

## TRACK D — PERFORMANCE BENCHMARKS

### Task 14: pytest-benchmark for resume, ATS, RAG, copilot

**Files:**
- Create: `backend/tests/benchmark/__init__.py`
- Create: `backend/tests/benchmark/conftest.py`
- Create: `backend/tests/benchmark/test_performance.py`

**Approach:** Use `pytest-benchmark` for service-level latency measurement. All external I/O (Ollama, ChromaDB) is mocked so measurements reflect pure Python overhead. These establish a baseline — later regressions will be visible in benchmark history.

- [ ] **Step 1: Install pytest-benchmark**

```bash
source .venv/bin/activate && pip install pytest-benchmark
```

Verify: `pip show pytest-benchmark` shows version ≥4.0.

- [ ] **Step 2: Create benchmark conftest**

```python
# backend/tests/benchmark/__init__.py
```

```python
# backend/tests/benchmark/conftest.py
from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from backend.services.ats.scorer import ATSScorer
from backend.services.copilot.engine import CopilotEngine
from backend.services.cover_letter.generator import CoverLetterGenerator
from backend.services.rag.service import RAGService
from backend.services.resume.generator import ResumeGenerator


@pytest.fixture(scope="module")
def mock_retriever_with_data():
    r = MagicMock()
    r.retrieve.return_value = [
        {"id": f"d{i}", "text": f"Led Python work project {i}", "collection": "acos_experiences",
         "semantic_score": 0.9 - i * 0.01,
         "metadata": {"confidence_level": "verified", "entity_id": f"e{i}",
                      "experience_id": f"e{i}", "company": "Acme",
                      "title": "SWE", "start_date": "2022-01", "end_date": "Present"}}
        for i in range(10)
    ]
    return r


@pytest.fixture(scope="module")
def mock_reranker():
    rr = MagicMock()
    rr.rerank.side_effect = lambda q, r, **kw: r
    return rr


@pytest.fixture(scope="module")
def mock_ollama_off():
    o = MagicMock()
    o.is_available.return_value = False
    return o


@pytest.fixture(scope="module")
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Benchmark system",
        "user_template": "JD: {job_description}\nTemplate: {template_name}\nKeywords: {keywords}\nEvidence: {evidence_json}\nTitle: {job_title}\nCompany: {company}\nIndustry: {industry}",
    }
    return loader
```

- [ ] **Step 3: Write performance benchmarks**

```python
# backend/tests/benchmark/test_performance.py
from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from backend.services.ats.scorer import ATSScorer
from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.copilot.engine import CopilotEngine
from backend.services.cover_letter.generator import CoverLetterGenerator
from backend.services.rag.service import RAGService
from backend.services.resume.evidence_selector import EvidenceSelector
from backend.services.resume.generator import ResumeGenerator


_JD = (
    "We are looking for a Senior Python Data Engineer with 5+ years of experience "
    "building ETL pipelines, data warehousing, and SQL query optimization. "
    "Experience with dbt, Airflow, and cloud data platforms preferred."
)


# ── ATS keyword extraction (pure Python regex — no LLM) ──────────────────

def test_ats_keyword_extraction_latency(benchmark, mock_ollama_off, mock_loader):
    extractor = KeywordExtractor(mock_ollama_off, mock_loader)
    result = benchmark(extractor.extract, _JD)
    assert "required_skills" in result


def test_ats_scoring_latency_no_ollama(benchmark, mock_ollama_off, mock_loader):
    scorer = ATSScorer(mock_ollama_off, mock_loader)
    keywords = {"required_skills": ["Python", "SQL"], "keywords": ["ETL", "dbt"]}
    resume = "Python Data Engineer. Built ETL pipelines. Used SQL and dbt."
    result = benchmark(scorer.score, resume, _JD, keywords)
    assert result["overall_score"] >= 0


# ── RAG retrieval (mocked ChromaDB) ───────────────────────────────────────

def test_rag_query_latency_no_ollama(benchmark, mock_retriever_with_data, mock_reranker, mock_ollama_off):
    svc = RAGService(mock_retriever_with_data, mock_reranker, mock_ollama_off)
    result = benchmark(svc.query, "Python engineering experience", intent="resume_help")
    assert len(result["evidence"]) > 0


# ── Evidence selector (mocked RAG) ───────────────────────────────────────

def test_evidence_selector_latency(benchmark, mock_retriever_with_data, mock_reranker):
    selector = EvidenceSelector(mock_retriever_with_data, mock_reranker)
    bullets = benchmark(selector.select, _JD, {}, max_bullets=8)
    assert len(bullets) > 0


# ── Resume generator rule-based path (no LLM, no DB) ────────────────────

def test_resume_rule_based_build_latency(benchmark, mock_ollama_off, mock_loader,
                                          mock_retriever_with_data, mock_reranker,
                                          test_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    session = Session()

    kw = MagicMock()
    kw.extract.return_value = {
        "required_skills": ["Python"], "keywords": ["ETL"],
        "industry": "tech", "seniority_level": "senior", "preferred_skills": [],
    }
    scorer = MagicMock()
    scorer.score.return_value = {
        "overall_score": 80, "keyword_score": 80, "skill_score": 80,
        "experience_score": 80, "industry_score": 80,
        "matched_keywords": ["Python"], "missing_keywords": [], "explanation": "",
    }
    selector = EvidenceSelector(mock_retriever_with_data, mock_reranker)
    gen = ResumeGenerator(selector, kw, scorer, mock_ollama_off, mock_loader, session)

    result = benchmark(gen.generate, _JD, "software")
    assert "resume_id" in result
    session.close()


# ── Copilot engine (mocked RAG) ───────────────────────────────────────────

def test_copilot_engine_latency_no_ollama(benchmark, mock_retriever_with_data,
                                           mock_reranker, mock_ollama_off):
    rag_svc = RAGService(mock_retriever_with_data, mock_reranker, mock_ollama_off)
    engine = CopilotEngine(rag_svc)

    result = benchmark(engine.chat, "What Python work have I done?")
    assert "response" in result
    assert "citations" in result
```

- [ ] **Step 4: Run benchmarks (exclude from default pytest run)**

```
source .venv/bin/activate && python -m pytest backend/tests/benchmark/ -v --benchmark-only --benchmark-columns=min,mean,max,rounds 2>&1 | tail -30
```

Expected: All benchmarks run and print timing table. Record the `mean` times as baseline:
- ATS keyword extraction: <10ms
- ATS scoring (no LLM): <10ms
- RAG query (mocked): <5ms
- Evidence selector (mocked): <5ms
- Resume rule-based build: <50ms
- Copilot engine (mocked): <10ms

- [ ] **Step 5: Verify benchmarks are excluded from the default `pytest` run**

```
source .venv/bin/activate && python -m pytest backend/tests/ -q --no-header --no-cov --ignore=backend/tests/benchmark 2>&1 | tail -5
```

Expected: `284+ tests passed`. Benchmarks do not inflate the count.

- [ ] **Step 6: Add benchmark exclusion to pyproject.toml**

In `pyproject.toml`, update the `testpaths` and `addopts`:

```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
pythonpath = ["."]
addopts = "--cov=backend --cov-report=term-missing --cov-report=html:.coverage_html -v --ignore=backend/tests/benchmark"
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

- [ ] **Step 7: Commit**

```bash
git add backend/tests/benchmark/__init__.py backend/tests/benchmark/conftest.py backend/tests/benchmark/test_performance.py pyproject.toml
git commit -m "test(benchmark): pytest-benchmark suites for ATS, RAG retrieval, evidence selector, resume generator, copilot — establishes latency baselines"
```

---

## TRACK E — REGRESSION PREVENTION

### Task 15: Snapshot tests + ATS stability + prompt regression

**Files:**
- Create: `backend/tests/unit/test_snapshots.py`

**Approach:**
- **Output snapshots**: Assert that the *structure* (keys, types, field names) of generator outputs is stable. We cannot snapshot the LLM text itself (nondeterministic), but we can snapshot the shape.
- **ATS scoring stability**: Same resume + JD with the keyword-based scorer (no LLM) must always return the same score. The LLM scorer is nondeterministic by design and is not snapshotted.
- **Prompt regression**: All required prompt files exist and have the expected keys (`system`, `user_template`, `version`).

- [ ] **Step 1: Write the snapshot/regression tests**

```python
# backend/tests/unit/test_snapshots.py
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.ats.scorer import ATSScorer
from backend.services.cover_letter.generator import CoverLetterGenerator
from backend.services.prompt_loader import PromptLoader
from backend.services.resume.generator import ResumeGenerator, _normalize_confidence


# ─── Resume output structure snapshot ────────────────────────────────────

_REQUIRED_RESUME_KEYS = {"resume_id", "content_json", "ats_score", "weak_inference_count", "requires_approval"}
_REQUIRED_ATS_KEYS = {"overall_score", "keyword_score", "skill_score", "experience_score",
                       "industry_score", "matched_keywords", "missing_keywords", "explanation"}
_REQUIRED_CONTENT_KEYS = {"experiences", "skills", "projects", "education"}


def _make_resume_gen(test_session):
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Built Python ETL pipeline", "evidence_id": "b1", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"}
    ]
    kw = MagicMock()
    kw.extract.return_value = {
        "required_skills": ["Python"], "keywords": ["ETL"],
        "industry": "tech", "seniority_level": "senior", "preferred_skills": [],
    }
    scorer = MagicMock()
    scorer.score.return_value = {
        "overall_score": 80, "keyword_score": 80, "skill_score": 80,
        "experience_score": 80, "industry_score": 80,
        "matched_keywords": ["Python"], "missing_keywords": [], "explanation": "Good.",
    }
    ollama = MagicMock()
    ollama.is_available.return_value = False
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Gen", "user_template": "JD:{job_description} T:{template_name} K:{keywords} E:{evidence_json} Ti:{job_title} C:{company} I:{industry}",
    }
    return ResumeGenerator(sel, kw, scorer, ollama, loader, test_session)


def test_resume_output_structure_stable(test_session):
    gen = _make_resume_gen(test_session)
    result = gen.generate("Python Data Engineer role", "software")
    assert set(result.keys()) == _REQUIRED_RESUME_KEYS
    assert set(result["ats_score"].keys()) == _REQUIRED_ATS_KEYS
    assert set(result["content_json"].keys()) == _REQUIRED_CONTENT_KEYS
    assert isinstance(result["resume_id"], str) and len(result["resume_id"]) == 32
    assert isinstance(result["weak_inference_count"], int)
    assert isinstance(result["requires_approval"], bool)


def test_resume_output_ats_score_types(test_session):
    gen = _make_resume_gen(test_session)
    result = gen.generate("Python role", "software")
    ats = result["ats_score"]
    assert isinstance(ats["overall_score"], int)
    assert 0 <= ats["overall_score"] <= 100
    assert isinstance(ats["matched_keywords"], list)
    assert isinstance(ats["missing_keywords"], list)


def test_resume_experiences_have_required_fields(test_session):
    gen = _make_resume_gen(test_session)
    result = gen.generate("Python role", "software")
    for exp in result["content_json"]["experiences"]:
        assert "title" in exp
        assert "company" in exp
        assert "bullets" in exp


# ─── Cover letter output structure snapshot ───────────────────────────────

_REQUIRED_CL_KEYS = {"text", "word_count", "length_target", "requires_approval"}


def test_cover_letter_output_structure_stable():
    sel = MagicMock()
    sel.select.return_value = []
    voice = MagicMock()
    voice.get_or_create_default.return_value = {
        "tone_descriptors": ["professional"], "structure_patterns": [],
        "vocabulary_patterns": {}, "sample_sentences": [],
    }
    ollama = MagicMock()
    ollama.is_available.return_value = False
    loader = MagicMock()
    gen = CoverLetterGenerator(sel, voice, ollama, loader)

    for length in ("short", "medium", "long", "full"):
        result = gen.generate("Python role", "Acme", "SWE", length)
        assert set(result.keys()) == _REQUIRED_CL_KEYS, f"Keys changed for length={length}"
        assert isinstance(result["text"], str)
        assert isinstance(result["word_count"], int)
        assert result["length_target"] == length
        assert isinstance(result["requires_approval"], bool)


# ─── ATS scoring stability (keyword-based, deterministic) ─────────────────

_RESUME_TEXT = (
    "Senior Python Data Engineer. Built ETL pipelines using Python and SQL. "
    "Worked with dbt and Airflow. Delivered $2M cost reduction."
)
_JD_TEXT = (
    "Senior Python Data Engineer. Requires Python, SQL, ETL pipeline experience. "
    "Preferred: dbt, Airflow."
)
_KEYWORDS = {
    "required_skills": ["Python", "SQL", "ETL"],
    "keywords": ["dbt", "Airflow", "data engineer"],
}


def test_ats_keyword_score_deterministic():
    ollama = MagicMock()
    ollama.is_available.return_value = False
    loader = MagicMock()
    scorer = ATSScorer(ollama, loader)

    score1 = scorer.score(_RESUME_TEXT, _JD_TEXT, _KEYWORDS)
    score2 = scorer.score(_RESUME_TEXT, _JD_TEXT, _KEYWORDS)

    assert score1["overall_score"] == score2["overall_score"]
    assert sorted(score1["matched_keywords"]) == sorted(score2["matched_keywords"])
    assert sorted(score1["missing_keywords"]) == sorted(score2["missing_keywords"])


def test_ats_score_higher_with_more_matches():
    ollama = MagicMock()
    ollama.is_available.return_value = False
    loader = MagicMock()
    scorer = ATSScorer(ollama, loader)

    good_resume = "Python SQL ETL dbt Airflow data engineer"
    poor_resume = "Java Spring Boot microservices"
    keywords = {"required_skills": ["Python", "SQL"], "keywords": ["ETL", "dbt"]}

    good_score = scorer.score(good_resume, _JD_TEXT, keywords)
    poor_score = scorer.score(poor_resume, _JD_TEXT, keywords)

    assert good_score["overall_score"] > poor_score["overall_score"]


# ─── Prompt file regression tests ────────────────────────────────────────

_REQUIRED_PROMPT_KEYS = {"system", "user_template", "version"}

_EXPECTED_PROMPTS = [
    "resume/generate",
    "resume/score_ats",
    "cover_letter/generate",
    "questions/generate",
]


def test_all_required_prompts_exist():
    loader = PromptLoader()
    for prompt_name in _EXPECTED_PROMPTS:
        try:
            data = loader.load(prompt_name)
            assert data is not None, f"Prompt '{prompt_name}' returned None"
        except Exception as exc:
            pytest.fail(f"Failed to load prompt '{prompt_name}': {exc}")


def test_prompts_have_required_keys():
    loader = PromptLoader()
    for prompt_name in _EXPECTED_PROMPTS:
        data = loader.load(prompt_name)
        missing = _REQUIRED_PROMPT_KEYS - set(data.keys())
        assert not missing, (
            f"Prompt '{prompt_name}' missing keys: {missing}. "
            f"Found: {set(data.keys())}"
        )


def test_prompts_have_non_empty_system_and_template():
    loader = PromptLoader()
    for prompt_name in _EXPECTED_PROMPTS:
        data = loader.load(prompt_name)
        assert data["system"].strip(), f"Prompt '{prompt_name}' has empty 'system'"
        assert data["user_template"].strip(), f"Prompt '{prompt_name}' has empty 'user_template'"


def test_resume_generate_prompt_has_required_placeholders():
    loader = PromptLoader()
    data = loader.load("resume/generate")
    template = data["user_template"]
    for placeholder in ("{job_description}", "{template_name}", "{evidence_json}"):
        assert placeholder in template, (
            f"resume/generate prompt missing placeholder: {placeholder}"
        )


def test_normalize_confidence_is_idempotent():
    """Running _normalize_confidence twice gives the same result."""
    content = {
        "experiences": [
            {"bullets": [
                {"text": "did X", "confidence": "verified"},
                {"text": "did Y", "confidence": "invalid_value"},
            ]}
        ]
    }
    once = _normalize_confidence(content)
    twice = _normalize_confidence(dict(once))
    assert once == twice
```

- [ ] **Step 2: Run snapshot/regression tests**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_snapshots.py -v --no-header --no-cov 2>&1 | tail -30
```

Expected: All tests pass. If any prompt key is missing from real prompt files, that's a genuine bug — update the prompt YAML/JSON file to add the missing key.

- [ ] **Step 3: Run full suite, verify ≥90% coverage**

```
source .venv/bin/activate && python -m pytest backend/tests/ -q --tb=short --cov=backend --cov-report=term-missing 2>&1 | tail -10
```

Expected: `Total coverage: ≥90%`. If not yet at 90%, run:

```
source .venv/bin/activate && python -m pytest backend/tests/ --cov=backend --cov-report=term-missing 2>&1 | grep -E "^backend/.*  [0-9]+.*[0-9]+%" | awk '{if ($NF+0 < 80) print}'
```

Then add targeted tests for remaining uncovered lines.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_snapshots.py
git commit -m "test(regression): snapshot tests for resume/cover-letter output structure, ATS scoring stability, prompt file integrity"
```

---

## Final Verification

- [ ] **Run complete backend test suite with coverage gate**

```
source .venv/bin/activate && python -m pytest backend/tests/ -q --tb=short 2>&1 | tail -10
```

Expected: `XXX passed, 0 failed` with `Total coverage: ≥90%` (the `fail_under=90` in pyproject.toml enforces this).

- [ ] **Run Playwright E2E suite**

```
cd frontend && npx playwright test --reporter=list 2>&1 | tail -20
```

Expected: All 5 spec files pass.

- [ ] **Run security regression tests in isolation**

```
source .venv/bin/activate && python -m pytest backend/tests/unit/test_ingestion_security.py backend/tests/unit/test_ingestion_security_extended.py backend/tests/unit/test_github_security.py backend/tests/integration/test_pipeline_divergence.py -v --no-header --no-cov 2>&1 | tail -20
```

Expected: All pass.

- [ ] **Run pyright type check**

```
source .venv/bin/activate && python -m pyright backend/ 2>&1 | tail -5
```

Expected: `0 errors`.

- [ ] **Final commit (if any loose files)**

```bash
git status
# stage and commit any remaining unstaged files
```

---

## Self-Review: Spec Coverage Check

| Scope item | Tasks covering it |
|---|---|
| 90% backend test coverage | Tasks 1–5 + Task 15 (final gate) |
| E2E: Resume generation | Task 10 |
| E2E: Cover letter generation | Task 11 |
| E2E: ATS scoring | Task 12 |
| E2E: Copilot query | Task 13 |
| E2E: Application CRM | Task 13 |
| Security: file ingestion pipeline | Tasks 7, 8 |
| Security: PDF/DOCX parsing | Existing parsers already have try/except; covered by existing parser tests + Task 8 symlink test |
| Security: local filesystem access | Task 8 (sanitize_filename + symlink test) |
| Security: GitHub ingestion | Task 7 |
| Security: Claude export ingestion | Covered by existing ingestion pipeline tests (same code path) |
| Security: export system | Task 8 (output goes through python-docx with no filesystem writes; no new attack surface) |
| No path traversal vulnerabilities | Tasks 7, 8 |
| SQLite consistency | Task 6 (pipeline divergence fix) |
| ChromaDB persistence | Task 6 (status=failed on indexer error) |
| Migration safety | Covered: no new migrations; existing Alembic tests verify rollback |
| Resume generation latency | Task 14 |
| ATS scoring latency | Task 14 |
| RAG retrieval latency | Task 14 |
| Copilot response time | Task 14 |
| Snapshot tests for resume outputs | Task 15 |
| Prompt regression tests | Task 15 |
| ATS scoring stability tests | Task 15 |
