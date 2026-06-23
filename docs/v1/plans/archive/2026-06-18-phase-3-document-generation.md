# Phase 3: Document Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build evidence-based resume and cover letter generation engines with ATS scoring, DOCX export, and a versioned prompt library — all grounded in the Phase 2 knowledge graph.

**Architecture:** A prompt library loads versioned YAML prompts; the ATS scorer extracts and matches keywords from job descriptions; the resume generator retrieves evidence from ChromaDB (Phase 2 RAG), selects bullets by confidence and relevance, applies one of six industry templates, and exports to DOCX; the cover letter engine learns a writing profile from historical letters and generates length-targeted output. All generated content traces to source `ExperienceBullet`, `Project`, or `Skill` records — no invented content.

**Tech Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.0 · python-docx 1.1.2 · pyyaml 6.0.2 · Ollama (Qwen3 8B) · ChromaDB (Phase 2 RAG)

## Global Constraints

- Python 3.12 venv at `.venv/` — `source .venv/bin/activate` before all commands
- UUID PKs: `uuid.uuid4().hex` — String(32), no hyphens
- Timestamps: ISO 8601 String(32) via `datetime.utcnow().isoformat()`
- Confidence levels: ONLY `verified | strong_inference | weak_inference`
- `weak_inference` bullets are flagged in output and must NOT be auto-exported — user approval required
- No hallucinated metrics, employers, certifications, or projects — every bullet traces to a source record
- `BaseRepository.create()` takes `**kwargs` keyword arguments, not a model instance
- Tests use `test_session` fixture (from `backend/tests/conftest.py`)
- LLM model: `settings.default_model` (default `"qwen3:8b"`)
- Embedding model: `settings.embedding_model` (default `"nomic-embed-text"`)
- `render_as_batch=True` in Alembic for any SQLite migrations
- TDD: failing test before implementation; ≥90% new-module coverage
- Resume templates: `software`, `ai`, `product`, `consulting`, `data_analytics`, `healthcare`
- Cover letter length targets (word counts): `short=100`, `medium=250`, `long=400`, `full=600`

---

## File Structure

```
backend/
├── services/
│   ├── prompt_loader.py              # Load + validate versioned YAML prompts
│   ├── ats/
│   │   ├── __init__.py
│   │   ├── keyword_extractor.py      # JD → keyword list (LLM + regex)
│   │   └── scorer.py                 # Keyword/skill/experience/industry scoring
│   ├── resume/
│   │   ├── __init__.py
│   │   ├── templates.py              # 6 industry template definitions
│   │   ├── evidence_selector.py      # RAG → ranked evidence bullets
│   │   ├── generator.py              # Orchestrate: select → format → score → enforce
│   │   └── docx_exporter.py          # content_json → DOCX bytes
│   └── cover_letter/
│       ├── __init__.py
│       ├── voice_modeler.py          # Learn WritingProfile from historical CLs
│       ├── generator.py              # Generate CL at target length
│       └── docx_exporter.py          # CL text → DOCX bytes
├── repositories/
│   └── resume.py                     # ResumeRepository, ResumeTemplateRepository, WritingProfileRepository
├── api/v1/routes/
│   ├── resume.py                     # POST /api/v1/resume/generate, POST /api/v1/resume/analyze-ats
│   └── cover_letter.py               # POST /api/v1/cover-letter/generate, POST /api/v1/cover-letter/learn-voice
├── prompts/
│   ├── resume/
│   │   ├── generate.yaml
│   │   ├── score_ats.yaml
│   │   └── extract_keywords.yaml
│   └── cover_letter/
│       ├── generate.yaml
│       └── learn_voice.yaml
└── tests/
    ├── unit/
    │   ├── test_prompt_loader.py
    │   ├── test_ats_keyword_extractor.py
    │   ├── test_ats_scorer.py
    │   ├── test_resume_templates.py
    │   ├── test_evidence_selector.py
    │   ├── test_resume_generator.py
    │   ├── test_resume_docx_exporter.py
    │   ├── test_voice_modeler.py
    │   └── test_cover_letter_generator.py
    └── integration/
        ├── test_resume_api.py
        └── test_cover_letter_api.py
```

---

### Task 1: Prompt Library System

**Files:**
- Create: `backend/services/prompt_loader.py`
- Create: `backend/prompts/resume/generate.yaml`
- Create: `backend/prompts/resume/score_ats.yaml`
- Create: `backend/prompts/resume/extract_keywords.yaml`
- Create: `backend/prompts/cover_letter/generate.yaml`
- Create: `backend/prompts/cover_letter/learn_voice.yaml`
- Create: `backend/tests/unit/test_prompt_loader.py`

**Interfaces:**
- Produces: `PromptLoader` with `.load(name: str) -> dict` returning `{version, system, user_template}`; raises `FileNotFoundError` if prompt missing; `name` uses slash notation e.g. `"resume/generate"`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_prompt_loader.py`:

```python
import pytest
from backend.services.prompt_loader import PromptLoader


def test_load_returns_required_keys():
    loader = PromptLoader()
    prompt = loader.load("resume/generate")
    assert "version" in prompt
    assert "system" in prompt
    assert "user_template" in prompt


def test_load_missing_prompt_raises():
    loader = PromptLoader()
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent/prompt")


def test_load_extract_keywords():
    loader = PromptLoader()
    prompt = loader.load("resume/extract_keywords")
    assert "{job_description}" in prompt["user_template"]


def test_load_cover_letter_generate():
    loader = PromptLoader()
    prompt = loader.load("cover_letter/generate")
    assert "{job_description}" in prompt["user_template"]
    assert "{length_target}" in prompt["user_template"]
```

- [ ] **Step 2: Run to verify failure**

```bash
source .venv/bin/activate
python -m pytest backend/tests/unit/test_prompt_loader.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` for `backend.services.prompt_loader`.

- [ ] **Step 3: Create prompt YAML files**

Create `backend/prompts/resume/generate.yaml`:
```yaml
version: "1.0"
system: |
  You are a professional resume writer. Generate evidence-based resume bullets using ONLY the
  provided evidence records. Never invent metrics, employers, technologies, or certifications.
  Each bullet must be traceable to exactly one evidence record.
  Rules:
  - Start every bullet with a strong action verb
  - Include quantifiable impact only when present in the evidence
  - Maximum 2 lines per bullet (≤25 words)
  - Do not include bullets with confidence_level "weak_inference" without flagging them

user_template: |
  Job Title: {job_title}
  Company: {company}
  Industry: {industry}
  Template: {template_name}

  Job Description Keywords: {keywords}

  Evidence Records (use ONLY these):
  {evidence_json}

  Generate a one-page resume in JSON format:
  {{
    "summary": "2-3 sentence professional summary",
    "experiences": [
      {{
        "title": "...", "company": "...", "dates": "...",
        "bullets": [{{"text": "...", "evidence_id": "...", "confidence": "..."}}]
      }}
    ],
    "skills": ["..."],
    "projects": [{{"name": "...", "description": "...", "tech": "...", "evidence_id": "..."}}],
    "education": []
  }}
  Return JSON only. No explanation.
```

Create `backend/prompts/resume/score_ats.yaml`:
```yaml
version: "1.0"
system: |
  You are an ATS (Applicant Tracking System) expert. Score the resume against the job description.
  Return ONLY valid JSON. No explanation outside the JSON.

user_template: |
  Job Description:
  {job_description}

  Resume Content:
  {resume_text}

  Score this resume on a 0-100 scale and return:
  {{
    "overall_score": 0-100,
    "keyword_score": 0-100,
    "skill_score": 0-100,
    "experience_score": 0-100,
    "industry_score": 0-100,
    "matched_keywords": ["..."],
    "missing_keywords": ["..."],
    "explanation": "2-3 sentence explanation of the score"
  }}
```

Create `backend/prompts/resume/extract_keywords.yaml`:
```yaml
version: "1.0"
system: |
  Extract the most important keywords and skills from this job description.
  Return ONLY valid JSON. No explanation outside the JSON.

user_template: |
  Job Description:
  {job_description}

  Return:
  {{
    "required_skills": ["..."],
    "preferred_skills": ["..."],
    "keywords": ["..."],
    "industry": "...",
    "seniority_level": "junior|mid|senior|lead|executive"
  }}
```

Create `backend/prompts/cover_letter/generate.yaml`:
```yaml
version: "1.0"
system: |
  You are writing a cover letter in the voice of the provided writing profile.
  Use ONLY the provided evidence records — never invent facts.
  Match the exact target word count specified.
  Rules:
  - Mirror the tone descriptors from the writing profile
  - Use vocabulary patterns from the profile
  - Every career claim must be traceable to an evidence record
  - End with a specific call to action

user_template: |
  Job Title: {job_title}
  Company: {company}
  Industry: {industry}
  Target Length: {length_target} words

  Writing Profile:
  Tone: {tone_descriptors}
  Vocabulary: {vocabulary_patterns}
  Sample Sentences: {sample_sentences}

  Evidence Records:
  {evidence_json}

  Job Keywords: {keywords}

  Write the cover letter body only (no date/address header). Target exactly {length_target} words.
```

Create `backend/prompts/cover_letter/learn_voice.yaml`:
```yaml
version: "1.0"
system: |
  Analyze the writing style of the provided cover letters.
  Return ONLY valid JSON. No explanation outside the JSON.

user_template: |
  Cover Letters:
  {cover_letter_texts}

  Analyze and return:
  {{
    "tone_descriptors": ["..."],
    "structure_patterns": ["..."],
    "vocabulary_patterns": {{"formal_phrases": ["..."], "transition_words": ["..."], "avoid": ["..."]}},
    "sample_sentences": ["..."]
  }}
```

- [ ] **Step 4: Implement PromptLoader**

Create `backend/services/prompt_loader.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class PromptLoader:
    def load(self, name: str) -> dict:
        path = _PROMPTS_DIR / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        with path.open() as f:
            data = yaml.safe_load(f)
        return {
            "version": data.get("version", "1.0"),
            "system": data.get("system", ""),
            "user_template": data.get("user_template", ""),
        }
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest backend/tests/unit/test_prompt_loader.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/services/prompt_loader.py backend/prompts/ backend/tests/unit/test_prompt_loader.py
git commit -m "feat: add versioned prompt library system with YAML prompts"
```

---

### Task 2: ATS Keyword Extractor

**Files:**
- Create: `backend/services/ats/__init__.py`
- Create: `backend/services/ats/keyword_extractor.py`
- Create: `backend/tests/unit/test_ats_keyword_extractor.py`

**Interfaces:**
- Consumes: `PromptLoader` from Task 1; `OllamaClient` from `backend/services/ollama_client.py`
- Produces: `KeywordExtractor(ollama_client, prompt_loader).extract(job_description: str) -> dict` returning `{required_skills, preferred_skills, keywords, industry, seniority_level}`; falls back to regex extraction if LLM unavailable

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_ats_keyword_extractor.py`:

```python
import json
from unittest.mock import MagicMock
import pytest
from backend.services.ats.keyword_extractor import KeywordExtractor


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "required_skills": ["Python", "SQL"],
        "preferred_skills": ["FastAPI"],
        "keywords": ["data engineering", "pipeline", "ETL"],
        "industry": "technology",
        "seniority_level": "senior",
    })
    return client


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Extract keywords",
        "user_template": "Job Description:\n{job_description}\n\nReturn JSON.",
    }
    return loader


def test_extract_returns_required_keys(mock_ollama, mock_loader):
    extractor = KeywordExtractor(mock_ollama, mock_loader)
    result = extractor.extract("Senior Python Engineer at Tech Co.")
    assert "required_skills" in result
    assert "preferred_skills" in result
    assert "keywords" in result
    assert "industry" in result
    assert "seniority_level" in result


def test_extract_llm_called_with_jd(mock_ollama, mock_loader):
    extractor = KeywordExtractor(mock_ollama, mock_loader)
    extractor.extract("Build Python data pipelines using SQL and ETL tools.")
    mock_ollama.generate.assert_called_once()
    call_kwargs = mock_ollama.generate.call_args
    prompt_text = call_kwargs[1].get("prompt") or call_kwargs[0][1]
    assert "Python" in prompt_text or "ETL" in prompt_text


def test_extract_falls_back_on_llm_failure(mock_loader):
    offline = MagicMock()
    offline.is_available.return_value = False
    extractor = KeywordExtractor(offline, mock_loader)
    result = extractor.extract("We need Python and SQL skills.")
    assert isinstance(result["required_skills"], list)
    assert isinstance(result["keywords"], list)


def test_extract_malformed_json_returns_empty(mock_ollama, mock_loader):
    mock_ollama.generate.return_value = "not json"
    extractor = KeywordExtractor(mock_ollama, mock_loader)
    result = extractor.extract("Some JD text")
    assert result["required_skills"] == []
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/unit/test_ats_keyword_extractor.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `__init__.py`**

Create `backend/services/ats/__init__.py` (empty).

- [ ] **Step 4: Implement keyword extractor**

Create `backend/services/ats/keyword_extractor.py`:

```python
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_EMPTY: dict[str, list | str] = {
    "required_skills": [],
    "preferred_skills": [],
    "keywords": [],
    "industry": "technology",
    "seniority_level": "mid",
}

_COMMON_SKILLS = re.compile(
    r"\b(python|sql|java|javascript|typescript|react|fastapi|postgresql|aws|docker|kubernetes|"
    r"machine learning|deep learning|nlp|pandas|numpy|scikit-learn|terraform|git|"
    r"data engineering|etl|pipeline|analytics|tableau|power bi|excel)\b",
    re.IGNORECASE,
)


class KeywordExtractor:
    def __init__(self, ollama_client, prompt_loader) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader

    def extract(self, job_description: str) -> dict:
        if not self._ollama or not self._ollama.is_available():
            return self._regex_fallback(job_description)
        try:
            prompt_data = self._loader.load("resume/extract_keywords")
            user = prompt_data["user_template"].format(job_description=job_description[:4000])
            raw = self._ollama.generate(
                model=None,
                prompt=user,
                temperature=0.1,
                system=prompt_data["system"],
            )
            data = json.loads(raw)
            return {
                "required_skills": data.get("required_skills", []),
                "preferred_skills": data.get("preferred_skills", []),
                "keywords": data.get("keywords", []),
                "industry": data.get("industry", "technology"),
                "seniority_level": data.get("seniority_level", "mid"),
            }
        except json.JSONDecodeError as exc:
            logger.warning("keyword_extractor: LLM returned invalid JSON: %s", exc)
            return dict(_EMPTY)
        except Exception as exc:
            logger.warning("keyword_extractor: LLM failed, using regex fallback: %s", exc)
            return self._regex_fallback(job_description)

    def _regex_fallback(self, text: str) -> dict:
        found = list({m.group(0).lower() for m in _COMMON_SKILLS.finditer(text)})
        return {
            "required_skills": found,
            "preferred_skills": [],
            "keywords": found,
            "industry": "technology",
            "seniority_level": "mid",
        }
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest backend/tests/unit/test_ats_keyword_extractor.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/services/ats/ backend/tests/unit/test_ats_keyword_extractor.py
git commit -m "feat: add ATS keyword extractor with LLM + regex fallback"
```

---

### Task 3: ATS Scoring Engine + Repository + API

**Files:**
- Create: `backend/services/ats/scorer.py`
- Create: `backend/repositories/resume.py`
- Create: `backend/api/v1/routes/resume.py`
- Modify: `backend/main.py` — register resume router
- Create: `backend/tests/unit/test_ats_scorer.py`
- Create: `backend/tests/integration/test_resume_api.py`

**Interfaces:**
- Consumes: `KeywordExtractor` (Task 2); `PromptLoader` (Task 1); models `Resume`, `ResumeTemplate`, `WritingProfile` from `backend/models/resume.py`
- Produces:
  - `ATSScorer(ollama_client, prompt_loader).score(resume_text: str, job_description: str, keywords: dict) -> dict`
    returning `{overall_score, keyword_score, skill_score, experience_score, industry_score, matched_keywords, missing_keywords, explanation}`
  - `ResumeRepository(session)` — CRUD for `Resume`; `ResumeTemplateRepository(session)` — CRUD for `ResumeTemplate`
  - `POST /api/v1/resume/analyze-ats` body: `{resume_text: str, job_description: str}`, returns score dict

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_ats_scorer.py`:

```python
import json
from unittest.mock import MagicMock
import pytest
from backend.services.ats.scorer import ATSScorer


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "overall_score": 82,
        "keyword_score": 85,
        "skill_score": 80,
        "experience_score": 78,
        "industry_score": 90,
        "matched_keywords": ["Python", "SQL", "pipeline"],
        "missing_keywords": ["Spark"],
        "explanation": "Strong Python match but missing big data skills.",
    })
    return client


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Score the resume.",
        "user_template": "JD:\n{job_description}\n\nResume:\n{resume_text}\n\nReturn JSON.",
    }
    return loader


def test_score_returns_all_keys(mock_ollama, mock_loader):
    scorer = ATSScorer(mock_ollama, mock_loader)
    result = scorer.score("Python developer resume text.", "Senior Python role", {})
    for key in ["overall_score", "keyword_score", "skill_score", "experience_score",
                "industry_score", "matched_keywords", "missing_keywords", "explanation"]:
        assert key in result


def test_score_clamps_between_0_and_100(mock_ollama, mock_loader):
    mock_ollama.generate.return_value = json.dumps({
        "overall_score": 150,
        "keyword_score": -5,
        "skill_score": 80,
        "experience_score": 80,
        "industry_score": 80,
        "matched_keywords": [],
        "missing_keywords": [],
        "explanation": "test",
    })
    scorer = ATSScorer(mock_ollama, mock_loader)
    result = scorer.score("resume", "jd", {})
    assert result["overall_score"] == 100
    assert result["keyword_score"] == 0


def test_score_keyword_fallback_no_llm(mock_loader):
    offline = MagicMock()
    offline.is_available.return_value = False
    scorer = ATSScorer(offline, mock_loader)
    keywords = {"required_skills": ["Python", "SQL"], "keywords": ["ETL", "Python"]}
    result = scorer.score("Python developer with SQL experience and ETL work.", "Python SQL ETL job", keywords)
    assert result["overall_score"] >= 0
    assert isinstance(result["matched_keywords"], list)


def test_score_malformed_json_returns_defaults(mock_ollama, mock_loader):
    mock_ollama.generate.return_value = "not json"
    scorer = ATSScorer(mock_ollama, mock_loader)
    result = scorer.score("resume", "jd", {})
    assert result["overall_score"] == 0
    assert result["explanation"] != ""
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/unit/test_ats_scorer.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement ATS scorer**

Create `backend/services/ats/scorer.py`:

```python
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_DEFAULT_RESULT: dict = {
    "overall_score": 0,
    "keyword_score": 0,
    "skill_score": 0,
    "experience_score": 0,
    "industry_score": 0,
    "matched_keywords": [],
    "missing_keywords": [],
    "explanation": "Scoring unavailable.",
}


def _clamp(value: int | float) -> int:
    return max(0, min(100, int(value)))


class ATSScorer:
    def __init__(self, ollama_client, prompt_loader) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader

    def score(self, resume_text: str, job_description: str, keywords: dict) -> dict:
        if self._ollama and self._ollama.is_available():
            return self._llm_score(resume_text, job_description)
        return self._keyword_score(resume_text, keywords)

    def _llm_score(self, resume_text: str, job_description: str) -> dict:
        try:
            prompt_data = self._loader.load("resume/score_ats")
            user = prompt_data["user_template"].format(
                job_description=job_description[:3000],
                resume_text=resume_text[:3000],
            )
            raw = self._ollama.generate(
                model=None,
                prompt=user,
                temperature=0.1,
                system=prompt_data["system"],
            )
            data = json.loads(raw)
            return {
                "overall_score": _clamp(data.get("overall_score", 0)),
                "keyword_score": _clamp(data.get("keyword_score", 0)),
                "skill_score": _clamp(data.get("skill_score", 0)),
                "experience_score": _clamp(data.get("experience_score", 0)),
                "industry_score": _clamp(data.get("industry_score", 0)),
                "matched_keywords": data.get("matched_keywords", []),
                "missing_keywords": data.get("missing_keywords", []),
                "explanation": data.get("explanation", ""),
            }
        except json.JSONDecodeError as exc:
            logger.warning("ats_scorer: invalid JSON from LLM: %s", exc)
            return dict(_DEFAULT_RESULT) | {"explanation": "LLM returned invalid response."}
        except Exception as exc:
            logger.warning("ats_scorer: LLM failed: %s", exc)
            return dict(_DEFAULT_RESULT) | {"explanation": str(exc)}

    def _keyword_score(self, resume_text: str, keywords: dict) -> dict:
        all_kw = (
            [k.lower() for k in keywords.get("required_skills", [])]
            + [k.lower() for k in keywords.get("keywords", [])]
        )
        resume_lower = resume_text.lower()
        matched = [k for k in all_kw if re.search(r"\b" + re.escape(k) + r"\b", resume_lower)]
        missing = [k for k in all_kw if k not in matched]
        score = int(100 * len(matched) / len(all_kw)) if all_kw else 0
        return {
            "overall_score": score,
            "keyword_score": score,
            "skill_score": score,
            "experience_score": score,
            "industry_score": 50,
            "matched_keywords": matched,
            "missing_keywords": missing,
            "explanation": f"Pattern-based score: {len(matched)}/{len(all_kw)} keywords matched.",
        }
```

- [ ] **Step 4: Create Resume repositories**

Create `backend/repositories/resume.py`:

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.resume import Resume, ResumeTemplate, WritingProfile
from backend.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, session: Session) -> None:
        super().__init__(Resume, session)

    def get_by_application(self, application_id: str) -> list[Resume]:
        stmt = select(Resume).where(Resume.application_id == application_id)
        return list(self.session.execute(stmt).scalars().all())

    def get_master(self) -> Resume | None:
        stmt = select(Resume).where(Resume.is_master == True)  # noqa: E712
        return self.session.execute(stmt).scalar_one_or_none()


class ResumeTemplateRepository(BaseRepository[ResumeTemplate]):
    def __init__(self, session: Session) -> None:
        super().__init__(ResumeTemplate, session)

    def get_default(self) -> ResumeTemplate | None:
        stmt = select(ResumeTemplate).where(ResumeTemplate.is_default == True)  # noqa: E712
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_industry(self, industry: str) -> ResumeTemplate | None:
        stmt = select(ResumeTemplate).where(ResumeTemplate.target_industry == industry)
        return self.session.execute(stmt).scalar_one_or_none()


class WritingProfileRepository(BaseRepository[WritingProfile]):
    def __init__(self, session: Session) -> None:
        super().__init__(WritingProfile, session)

    def get_latest(self) -> WritingProfile | None:
        stmt = select(WritingProfile).order_by(WritingProfile.updated_at.desc()).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()
```

- [ ] **Step 5: Create resume API route**

Create `backend/api/v1/routes/resume.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.ats.scorer import ATSScorer
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader

router = APIRouter(tags=["resume"])


class ATSRequest(BaseModel):
    resume_text: str
    job_description: str


@router.post("/resume/analyze-ats")
def analyze_ats(body: ATSRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    loader = PromptLoader()
    extractor = KeywordExtractor(ollama, loader)
    scorer = ATSScorer(ollama, loader)

    keywords = extractor.extract(body.job_description)
    score = scorer.score(body.resume_text, body.job_description, keywords)
    return {"keywords": keywords, "ats_score": score}
```

- [ ] **Step 6: Register route in main.py**

Read `backend/main.py`, add after the RAG router:

```python
from backend.api.v1.routes.resume import router as resume_router
# ...
app.include_router(resume_router, prefix="/api/v1")
```

- [ ] **Step 7: Run unit tests**

```bash
python -m pytest backend/tests/unit/test_ats_scorer.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 8: Commit**

```bash
git add backend/services/ats/scorer.py backend/repositories/resume.py \
        backend/api/v1/routes/resume.py backend/main.py \
        backend/tests/unit/test_ats_scorer.py
git commit -m "feat: add ATS scoring engine, resume repository, and POST /api/v1/resume/analyze-ats"
```

---

### Task 4: Resume Template System + Evidence Selector

**Files:**
- Create: `backend/services/resume/templates.py`
- Create: `backend/services/resume/evidence_selector.py`
- Create: `backend/tests/unit/test_resume_templates.py`
- Create: `backend/tests/unit/test_evidence_selector.py`

**Interfaces:**
- Produces:
  - `RESUME_TEMPLATES: dict[str, dict]` — 6 template defs; `get_template(name: str) -> dict` — raises `ValueError` if unknown
  - `EvidenceSelector(rag_retriever, reranker).select(job_description: str, keywords: dict, max_bullets: int = 8) -> list[dict]`
    returning list of `{bullet_text, experience_id, company, title, dates, confidence, evidence_id}`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_resume_templates.py`:

```python
import pytest
from backend.services.resume.templates import get_template, RESUME_TEMPLATES, TEMPLATE_NAMES


def test_all_six_templates_defined():
    assert set(TEMPLATE_NAMES) == {"software", "ai", "product", "consulting", "data_analytics", "healthcare"}


def test_get_template_returns_dict():
    for name in TEMPLATE_NAMES:
        tmpl = get_template(name)
        assert "sections" in tmpl
        assert "layout" in tmpl


def test_get_template_unknown_raises():
    with pytest.raises(ValueError, match="Unknown template"):
        get_template("nonexistent")


def test_software_template_has_skills_section():
    tmpl = get_template("software")
    assert "skills" in tmpl["sections"]


def test_consulting_template_has_impact_section():
    tmpl = get_template("consulting")
    assert tmpl["bullet_style"] == "star"
```

Create `backend/tests/unit/test_evidence_selector.py`:

```python
from unittest.mock import MagicMock
import pytest
from backend.services.resume.evidence_selector import EvidenceSelector


@pytest.fixture
def mock_retriever():
    r = MagicMock()
    r.retrieve.return_value = [
        {
            "id": "b1",
            "text": "Built Python ETL pipeline processing 10M records daily",
            "metadata": {
                "confidence_level": "verified",
                "experience_id": "exp1",
                "company": "Acme Corp",
                "title": "Data Engineer",
                "start_date": "2022-01",
                "end_date": "2024-01",
                "entity_id": "b1",
            },
            "semantic_score": 0.92,
            "collection": "acos_experiences",
        }
    ]
    return r


@pytest.fixture
def mock_reranker():
    r = MagicMock()
    r.rerank.return_value = [
        {
            "id": "b1",
            "text": "Built Python ETL pipeline processing 10M records daily",
            "metadata": {
                "confidence_level": "verified",
                "experience_id": "exp1",
                "company": "Acme Corp",
                "title": "Data Engineer",
                "start_date": "2022-01",
                "end_date": "2024-01",
                "entity_id": "b1",
            },
            "semantic_score": 0.92,
            "combined_score": 1.1,
            "collection": "acos_experiences",
        }
    ]
    return r


def test_select_returns_bullets(mock_retriever, mock_reranker):
    selector = EvidenceSelector(mock_retriever, mock_reranker)
    results = selector.select("Python data engineer role", {"required_skills": ["Python"]})
    assert len(results) == 1
    assert results[0]["bullet_text"] == "Built Python ETL pipeline processing 10M records daily"


def test_select_includes_confidence(mock_retriever, mock_reranker):
    selector = EvidenceSelector(mock_retriever, mock_reranker)
    results = selector.select("Python role", {})
    assert results[0]["confidence"] == "verified"


def test_select_limits_to_max_bullets(mock_retriever, mock_reranker):
    # Return 10 results from reranker
    item = mock_reranker.rerank.return_value[0]
    mock_reranker.rerank.return_value = [
        {**item, "id": str(i), "metadata": {**item["metadata"], "entity_id": str(i)}}
        for i in range(10)
    ]
    selector = EvidenceSelector(mock_retriever, mock_reranker)
    results = selector.select("Python role", {}, max_bullets=3)
    assert len(results) <= 3
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/unit/test_resume_templates.py backend/tests/unit/test_evidence_selector.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create resume service `__init__.py`**

Create `backend/services/resume/__init__.py` (empty).

- [ ] **Step 4: Implement templates**

Create `backend/services/resume/templates.py`:

```python
from __future__ import annotations

TEMPLATE_NAMES = ["software", "ai", "product", "consulting", "data_analytics", "healthcare"]

RESUME_TEMPLATES: dict[str, dict] = {
    "software": {
        "layout": "single_column",
        "bullet_style": "action_impact",
        "sections": ["summary", "experience", "skills", "projects", "education"],
        "skills_position": "after_experience",
        "max_experience_bullets": 4,
        "emphasis": "technical_depth",
    },
    "ai": {
        "layout": "single_column",
        "bullet_style": "action_impact",
        "sections": ["summary", "experience", "projects", "skills", "education"],
        "skills_position": "after_projects",
        "max_experience_bullets": 3,
        "emphasis": "research_and_systems",
    },
    "product": {
        "layout": "single_column",
        "bullet_style": "metrics_first",
        "sections": ["summary", "experience", "skills", "education"],
        "skills_position": "end",
        "max_experience_bullets": 4,
        "emphasis": "stakeholder_impact",
    },
    "consulting": {
        "layout": "single_column",
        "bullet_style": "star",
        "sections": ["summary", "experience", "education", "skills"],
        "skills_position": "end",
        "max_experience_bullets": 4,
        "emphasis": "client_outcomes",
    },
    "data_analytics": {
        "layout": "single_column",
        "bullet_style": "action_impact",
        "sections": ["summary", "experience", "skills", "projects", "education"],
        "skills_position": "after_experience",
        "max_experience_bullets": 4,
        "emphasis": "data_tools_and_business_impact",
    },
    "healthcare": {
        "layout": "single_column",
        "bullet_style": "action_impact",
        "sections": ["summary", "experience", "education", "certifications", "skills"],
        "skills_position": "end",
        "max_experience_bullets": 4,
        "emphasis": "clinical_and_compliance",
    },
}


def get_template(name: str) -> dict:
    if name not in RESUME_TEMPLATES:
        raise ValueError(f"Unknown template: '{name}'. Valid: {TEMPLATE_NAMES}")
    return RESUME_TEMPLATES[name]
```

- [ ] **Step 5: Implement evidence selector**

Create `backend/services/resume/evidence_selector.py`:

```python
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_EXPERIENCE_COLLECTIONS = ["acos_experiences", "acos_projects", "acos_skills"]


class EvidenceSelector:
    def __init__(self, rag_retriever, reranker) -> None:
        self._retriever = rag_retriever
        self._reranker = reranker

    def select(
        self, job_description: str, keywords: dict, max_bullets: int = 8
    ) -> list[dict]:
        raw = self._retriever.retrieve(
            query=job_description,
            collections=_EXPERIENCE_COLLECTIONS,
            top_k=20,
        )
        ranked = self._reranker.rerank(
            query=job_description,
            results=raw,
            final_k=max_bullets,
        )
        return [self._to_bullet(r) for r in ranked[:max_bullets]]

    def _to_bullet(self, result: dict) -> dict:
        meta = result["metadata"]
        return {
            "bullet_text": result["text"],
            "evidence_id": result["id"],
            "experience_id": meta.get("experience_id", ""),
            "company": meta.get("company", ""),
            "title": meta.get("title", ""),
            "dates": f"{meta.get('start_date', '')}–{meta.get('end_date', 'Present')}",
            "confidence": meta.get("confidence_level", "strong_inference"),
        }
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest backend/tests/unit/test_resume_templates.py backend/tests/unit/test_evidence_selector.py -v
```

Expected: 8 tests PASSED.

- [ ] **Step 7: Commit**

```bash
git add backend/services/resume/ backend/tests/unit/test_resume_templates.py \
        backend/tests/unit/test_evidence_selector.py
git commit -m "feat: add resume template system and RAG-based evidence selector"
```

---

### Task 5: Resume Generator

**Files:**
- Create: `backend/services/resume/generator.py`
- Create: `backend/tests/unit/test_resume_generator.py`

**Interfaces:**
- Consumes: `EvidenceSelector` (Task 4), `ATSScorer` (Task 3), `KeywordExtractor` (Task 2), `PromptLoader` (Task 1), `ResumeRepository` (Task 3), `get_template` (Task 4)
- Produces: `ResumeGenerator(evidence_selector, keyword_extractor, ats_scorer, ollama_client, prompt_loader, session).generate(job_description, template_name, application_id=None) -> dict`
  returning `{resume_id, content_json, ats_score, weak_inference_count, requires_approval}`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_resume_generator.py`:

```python
import json
from unittest.mock import MagicMock
import pytest
from backend.services.resume.generator import ResumeGenerator


@pytest.fixture
def mock_evidence_selector():
    sel = MagicMock()
    sel.select.return_value = [
        {
            "bullet_text": "Built Python ETL pipeline reducing processing time by 40%",
            "evidence_id": "b1",
            "experience_id": "exp1",
            "company": "Acme Corp",
            "title": "Data Engineer",
            "dates": "2022-01–2024-01",
            "confidence": "verified",
        }
    ]
    return sel


@pytest.fixture
def mock_kw_extractor():
    ext = MagicMock()
    ext.extract.return_value = {
        "required_skills": ["Python", "ETL"],
        "preferred_skills": [],
        "keywords": ["data pipeline", "Python"],
        "industry": "technology",
        "seniority_level": "senior",
    }
    return ext


@pytest.fixture
def mock_ats_scorer():
    scorer = MagicMock()
    scorer.score.return_value = {
        "overall_score": 85,
        "keyword_score": 88,
        "skill_score": 82,
        "experience_score": 80,
        "industry_score": 90,
        "matched_keywords": ["Python", "ETL"],
        "missing_keywords": [],
        "explanation": "Strong match.",
    }
    return scorer


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "summary": "Senior Data Engineer with Python expertise.",
        "experiences": [{"title": "Data Engineer", "company": "Acme Corp", "dates": "2022–2024",
                         "bullets": [{"text": "Built Python ETL pipeline", "evidence_id": "b1", "confidence": "verified"}]}],
        "skills": ["Python", "ETL", "SQL"],
        "projects": [],
        "education": [],
    })
    return client


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Generate resume",
        "user_template": "JD: {job_description}\nTemplate: {template_name}\nKeywords: {keywords}\nEvidence: {evidence_json}",
    }
    return loader


def test_generate_returns_required_keys(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama, mock_loader, test_session
):
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama, mock_loader, test_session
    )
    result = gen.generate("Python data engineering role at Acme", "software")
    for key in ["resume_id", "content_json", "ats_score", "weak_inference_count", "requires_approval"]:
        assert key in result


def test_generate_no_weak_inference_no_approval(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama, mock_loader, test_session
):
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama, mock_loader, test_session
    )
    result = gen.generate("Python role", "software")
    assert result["weak_inference_count"] == 0
    assert result["requires_approval"] is False


def test_generate_weak_inference_sets_approval(
    mock_kw_extractor, mock_ats_scorer, mock_ollama, mock_loader, test_session
):
    sel = MagicMock()
    sel.select.return_value = [
        {
            "bullet_text": "Possibly led a team",
            "evidence_id": "w1",
            "experience_id": "exp1",
            "company": "Corp",
            "title": "Manager",
            "dates": "2020–2021",
            "confidence": "weak_inference",
        }
    ]
    gen = ResumeGenerator(sel, mock_kw_extractor, mock_ats_scorer, mock_ollama, mock_loader, test_session)
    result = gen.generate("Management role", "consulting")
    assert result["requires_approval"] is True


def test_generate_saves_resume_to_db(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama, mock_loader, test_session
):
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama, mock_loader, test_session
    )
    result = gen.generate("Python role", "software")
    assert result["resume_id"] is not None
    assert len(result["resume_id"]) == 32
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/unit/test_resume_generator.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement generator**

Create `backend/services/resume/generator.py`:

```python
from __future__ import annotations

import json
import logging
from sqlalchemy.orm import Session

from backend.repositories.resume import ResumeRepository
from backend.services.resume.templates import get_template

logger = logging.getLogger(__name__)


class ResumeGenerator:
    def __init__(
        self,
        evidence_selector,
        keyword_extractor,
        ats_scorer,
        ollama_client,
        prompt_loader,
        session: Session,
    ) -> None:
        self._selector = evidence_selector
        self._kw_extractor = keyword_extractor
        self._ats_scorer = ats_scorer
        self._ollama = ollama_client
        self._loader = prompt_loader
        self._resume_repo = ResumeRepository(session)

    def generate(
        self,
        job_description: str,
        template_name: str,
        application_id: str | None = None,
    ) -> dict:
        template = get_template(template_name)
        keywords = self._kw_extractor.extract(job_description)
        max_bullets = template.get("max_experience_bullets", 4) * 3

        evidence = self._selector.select(job_description, keywords, max_bullets=max_bullets)
        weak_count = sum(1 for e in evidence if e.get("confidence") == "weak_inference")

        content_json = self._build_content(job_description, template_name, keywords, evidence)
        resume_text = self._content_to_text(content_json)
        ats_score = self._ats_scorer.score(resume_text, job_description, keywords)

        resume = self._resume_repo.create(
            name=f"Resume — {keywords.get('industry', 'general')} ({template_name})",
            application_id=application_id,
            content_json=content_json,
            ats_score=float(ats_score["overall_score"]),
            page_count=1,
            is_master=False,
        )

        return {
            "resume_id": resume.id,
            "content_json": content_json,
            "ats_score": ats_score,
            "weak_inference_count": weak_count,
            "requires_approval": weak_count > 0,
        }

    def _build_content(
        self,
        job_description: str,
        template_name: str,
        keywords: dict,
        evidence: list[dict],
    ) -> dict:
        if self._ollama and self._ollama.is_available():
            return self._llm_build(job_description, template_name, keywords, evidence)
        return self._rule_based_build(template_name, evidence)

    def _llm_build(
        self,
        job_description: str,
        template_name: str,
        keywords: dict,
        evidence: list[dict],
    ) -> dict:
        try:
            prompt_data = self._loader.load("resume/generate")
            evidence_json = json.dumps([
                {"text": e["bullet_text"], "confidence": e["confidence"],
                 "evidence_id": e["evidence_id"], "company": e["company"],
                 "title": e["title"], "dates": e["dates"]}
                for e in evidence
            ], indent=2)
            user = prompt_data["user_template"].format(
                job_description=job_description[:2000],
                job_title="",
                company="",
                industry=keywords.get("industry", ""),
                template_name=template_name,
                keywords=", ".join(keywords.get("required_skills", []) + keywords.get("keywords", [])),
                evidence_json=evidence_json,
            )
            raw = self._ollama.generate(
                model=None,
                prompt=user,
                temperature=0.2,
                system=prompt_data["system"],
            )
            return json.loads(raw)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("resume_generator: LLM build failed (%s), using rule-based", exc)
            return self._rule_based_build(template_name, evidence)

    def _rule_based_build(self, template_name: str, evidence: list[dict]) -> dict:
        by_exp: dict[str, dict] = {}
        for e in evidence:
            key = e.get("experience_id") or e["evidence_id"]
            if key not in by_exp:
                by_exp[key] = {
                    "title": e.get("title", ""),
                    "company": e.get("company", ""),
                    "dates": e.get("dates", ""),
                    "bullets": [],
                }
            by_exp[key]["bullets"].append({
                "text": e["bullet_text"],
                "evidence_id": e["evidence_id"],
                "confidence": e["confidence"],
            })
        return {
            "summary": "",
            "experiences": list(by_exp.values()),
            "skills": [],
            "projects": [],
            "education": [],
        }

    def _content_to_text(self, content_json: dict) -> str:
        parts = [content_json.get("summary", "")]
        for exp in content_json.get("experiences", []):
            parts.append(f"{exp.get('title', '')} at {exp.get('company', '')}")
            for b in exp.get("bullets", []):
                parts.append(b.get("text", "") if isinstance(b, dict) else str(b))
        parts.extend(content_json.get("skills", []))
        return "\n".join(p for p in parts if p)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest backend/tests/unit/test_resume_generator.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/services/resume/generator.py backend/tests/unit/test_resume_generator.py
git commit -m "feat: add evidence-based resume generator with template routing and ATS scoring"
```

---

### Task 6: Resume DOCX Exporter

**Files:**
- Create: `backend/services/resume/docx_exporter.py`
- Create: `backend/tests/unit/test_resume_docx_exporter.py`

**Interfaces:**
- Consumes: `content_json: dict` (from `ResumeGenerator.generate()`); python-docx
- Produces: `ResumeDOCXExporter().export(content_json: dict, template_name: str) -> bytes` — DOCX file bytes; raises no exceptions (log and return minimal doc on error)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_resume_docx_exporter.py`:

```python
import io
import pytest
from docx import Document
from backend.services.resume.docx_exporter import ResumeDOCXExporter

_SAMPLE_CONTENT = {
    "summary": "Senior Data Engineer with 5 years of Python expertise.",
    "experiences": [
        {
            "title": "Data Engineer",
            "company": "Acme Corp",
            "dates": "2022–2024",
            "bullets": [
                {"text": "Built ETL pipeline in Python.", "evidence_id": "b1", "confidence": "verified"},
                {"text": "Maybe led a team.", "evidence_id": "b2", "confidence": "weak_inference"},
            ],
        }
    ],
    "skills": ["Python", "SQL", "ETL"],
    "projects": [{"name": "ACOS", "description": "Career OS", "tech": "Python/FastAPI", "evidence_id": "p1"}],
    "education": [],
}


def test_export_returns_bytes():
    exporter = ResumeDOCXExporter()
    result = exporter.export(_SAMPLE_CONTENT, "software")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_export_produces_valid_docx():
    exporter = ResumeDOCXExporter()
    result = exporter.export(_SAMPLE_CONTENT, "software")
    doc = Document(io.BytesIO(result))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Data Engineer" in text
    assert "Acme Corp" in text


def test_export_flags_weak_inference():
    exporter = ResumeDOCXExporter()
    result = exporter.export(_SAMPLE_CONTENT, "software")
    doc = Document(io.BytesIO(result))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "⚠" in text or "[REVIEW REQUIRED]" in text


def test_export_includes_skills():
    exporter = ResumeDOCXExporter()
    result = exporter.export(_SAMPLE_CONTENT, "software")
    doc = Document(io.BytesIO(result))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Python" in text
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/unit/test_resume_docx_exporter.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement DOCX exporter**

Create `backend/services/resume/docx_exporter.py`:

```python
from __future__ import annotations

import io
import logging
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

_WEAK_MARKER = "⚠ [REVIEW REQUIRED]"


class ResumeDOCXExporter:
    def export(self, content_json: dict, template_name: str) -> bytes:
        try:
            doc = Document()
            self._set_margins(doc)
            self._add_summary(doc, content_json.get("summary", ""))
            self._add_experiences(doc, content_json.get("experiences", []))
            self._add_skills(doc, content_json.get("skills", []))
            self._add_projects(doc, content_json.get("projects", []))
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
        except Exception as exc:
            logger.error("docx_exporter: failed to generate DOCX: %s", exc)
            doc = Document()
            doc.add_paragraph("Resume generation error. Please try again.")
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()

    def _set_margins(self, doc: Document) -> None:
        for section in doc.sections:
            section.top_margin = Pt(36)
            section.bottom_margin = Pt(36)
            section.left_margin = Pt(54)
            section.right_margin = Pt(54)

    def _add_summary(self, doc: Document, summary: str) -> None:
        if not summary:
            return
        doc.add_heading("Summary", level=2)
        doc.add_paragraph(summary)

    def _add_experiences(self, doc: Document, experiences: list[dict]) -> None:
        if not experiences:
            return
        doc.add_heading("Experience", level=2)
        for exp in experiences:
            p = doc.add_paragraph()
            run = p.add_run(f"{exp.get('title', '')} — {exp.get('company', '')}")
            run.bold = True
            p.add_run(f"  {exp.get('dates', '')}")
            for bullet in exp.get("bullets", []):
                if isinstance(bullet, dict):
                    text = bullet.get("text", "")
                    confidence = bullet.get("confidence", "verified")
                else:
                    text = str(bullet)
                    confidence = "verified"
                bullet_para = doc.add_paragraph(style="List Bullet")
                if confidence == "weak_inference":
                    run = bullet_para.add_run(f"{_WEAK_MARKER} {text}")
                    run.font.color.rgb = RGBColor(0xFF, 0x80, 0x00)
                else:
                    bullet_para.add_run(text)

    def _add_skills(self, doc: Document, skills: list[str]) -> None:
        if not skills:
            return
        doc.add_heading("Skills", level=2)
        doc.add_paragraph(" · ".join(skills))

    def _add_projects(self, doc: Document, projects: list[dict]) -> None:
        if not projects:
            return
        doc.add_heading("Projects", level=2)
        for proj in projects:
            p = doc.add_paragraph()
            run = p.add_run(proj.get("name", ""))
            run.bold = True
            desc = proj.get("description", "")
            tech = proj.get("tech", "")
            if desc:
                p.add_run(f" — {desc}")
            if tech:
                p.add_run(f" [{tech}]")
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest backend/tests/unit/test_resume_docx_exporter.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/services/resume/docx_exporter.py backend/tests/unit/test_resume_docx_exporter.py
git commit -m "feat: add resume DOCX exporter with weak_inference flagging"
```

---

### Task 7: Resume Generate API Route

**Files:**
- Modify: `backend/api/v1/routes/resume.py` — add `POST /api/v1/resume/generate` and `POST /api/v1/resume/generate/download`
- Create: `backend/tests/integration/test_resume_api.py`

**Interfaces:**
- Consumes: `ResumeGenerator` (Task 5), `ResumeDOCXExporter` (Task 6), `EvidenceSelector` (Task 4), `KeywordExtractor` (Task 2), `ATSScorer` (Task 3)
- Produces:
  - `POST /api/v1/resume/generate` body: `{job_description, template_name, application_id?}` → `{resume_id, ats_score, weak_inference_count, requires_approval, content_json}`
  - `POST /api/v1/resume/generate/download` body: same → DOCX file response

- [ ] **Step 1: Write failing tests**

Create `backend/tests/integration/test_resume_api.py`:

```python
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app):
    return TestClient(app)


def test_analyze_ats_returns_score(client):
    with patch("backend.api.v1.routes.resume.OllamaClient") as mock_cls:
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        resp = client.post("/api/v1/resume/analyze-ats", json={
            "resume_text": "Python developer with SQL skills",
            "job_description": "Senior Python engineer needed",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "ats_score" in data
    assert "keywords" in data


def test_generate_resume_returns_structure(client):
    with patch("backend.api.v1.routes.resume.OllamaClient") as mock_cls, \
         patch("backend.api.v1.routes.resume.RAGRetriever") as mock_ret_cls, \
         patch("backend.api.v1.routes.resume.Reranker") as mock_rerank_cls:
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        mock_ret_cls.return_value = mock_retriever

        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = []
        mock_rerank_cls.return_value = mock_reranker

        resp = client.post("/api/v1/resume/generate", json={
            "job_description": "Python data engineer role",
            "template_name": "software",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "resume_id" in data
    assert "ats_score" in data
    assert "requires_approval" in data


def test_generate_resume_invalid_template(client):
    resp = client.post("/api/v1/resume/generate", json={
        "job_description": "Python role",
        "template_name": "nonexistent_template",
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/integration/test_resume_api.py -v 2>&1 | head -20
```

Expected: import errors or 422 on generate endpoint.

- [ ] **Step 3: Expand resume route**

Update `backend/api/v1/routes/resume.py` — read the existing file first, then add the generate endpoint:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.ats.scorer import ATSScorer
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader
from backend.services.resume.docx_exporter import ResumeDOCXExporter
from backend.services.resume.evidence_selector import EvidenceSelector
from backend.services.resume.generator import ResumeGenerator
from backend.services.resume.templates import TEMPLATE_NAMES

router = APIRouter(tags=["resume"])

_VALID_TEMPLATES = set(TEMPLATE_NAMES)


class ATSRequest(BaseModel):
    resume_text: str
    job_description: str


class GenerateRequest(BaseModel):
    job_description: str
    template_name: str = "software"
    application_id: str | None = None


def _build_deps(settings):
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    loader = PromptLoader()
    extractor = KeywordExtractor(ollama, loader)
    scorer = ATSScorer(ollama, loader)
    selector = EvidenceSelector(retriever, reranker)
    return ollama, loader, extractor, scorer, selector


@router.post("/resume/analyze-ats")
def analyze_ats(body: ATSRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    ollama, loader, extractor, scorer, _ = _build_deps(settings)
    keywords = extractor.extract(body.job_description)
    score = scorer.score(body.resume_text, body.job_description, keywords)
    return {"keywords": keywords, "ats_score": score}


@router.post("/resume/generate")
def generate_resume(body: GenerateRequest, session: Session = Depends(get_session)):
    if body.template_name not in _VALID_TEMPLATES:
        raise HTTPException(status_code=422, detail=f"Invalid template: {body.template_name}. Valid: {TEMPLATE_NAMES}")
    settings = get_settings()
    ollama, loader, extractor, scorer, selector = _build_deps(settings)
    gen = ResumeGenerator(selector, extractor, scorer, ollama, loader, session)
    return gen.generate(body.job_description, body.template_name, body.application_id)


@router.post("/resume/generate/download")
def generate_resume_docx(body: GenerateRequest, session: Session = Depends(get_session)):
    if body.template_name not in _VALID_TEMPLATES:
        raise HTTPException(status_code=422, detail=f"Invalid template: {body.template_name}.")
    settings = get_settings()
    ollama, loader, extractor, scorer, selector = _build_deps(settings)
    gen = ResumeGenerator(selector, extractor, scorer, ollama, loader, session)
    result = gen.generate(body.job_description, body.template_name, body.application_id)
    exporter = ResumeDOCXExporter()
    docx_bytes = exporter.export(result["content_json"], body.template_name)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=resume.docx"},
    )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest backend/tests/integration/test_resume_api.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/api/v1/routes/resume.py backend/tests/integration/test_resume_api.py
git commit -m "feat: add POST /api/v1/resume/generate and /download endpoints"
```

---

### Task 8: Cover Letter Voice Modeler

**Files:**
- Create: `backend/services/cover_letter/__init__.py`
- Create: `backend/services/cover_letter/voice_modeler.py`
- Create: `backend/tests/unit/test_voice_modeler.py`

**Interfaces:**
- Consumes: `PromptLoader` (Task 1), `OllamaClient`, `WritingProfileRepository` (Task 3)
- Produces: `VoiceModeler(ollama_client, prompt_loader, session).learn(source_texts: list[str]) -> dict`
  returning `{profile_id, tone_descriptors, structure_patterns, vocabulary_patterns, sample_sentences}`; also `.get_or_create_default() -> dict` for offline fallback

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_voice_modeler.py`:

```python
import json
from unittest.mock import MagicMock
import pytest
from backend.services.cover_letter.voice_modeler import VoiceModeler


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "tone_descriptors": ["professional", "confident", "concise"],
        "structure_patterns": ["opens with hook", "leads with value"],
        "vocabulary_patterns": {
            "formal_phrases": ["I am excited to"],
            "transition_words": ["furthermore", "additionally"],
            "avoid": ["I feel", "I think"],
        },
        "sample_sentences": ["I bring a track record of delivering measurable outcomes."],
    })
    return client


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Analyze writing style.",
        "user_template": "Cover Letters:\n{cover_letter_texts}\n\nReturn JSON.",
    }
    return loader


def test_learn_returns_required_keys(mock_ollama, mock_loader, test_session):
    modeler = VoiceModeler(mock_ollama, mock_loader, test_session)
    result = modeler.learn(["Dear Hiring Manager, I am writing to express my interest..."])
    for key in ["profile_id", "tone_descriptors", "structure_patterns", "vocabulary_patterns", "sample_sentences"]:
        assert key in result


def test_learn_saves_to_db(mock_ollama, mock_loader, test_session):
    modeler = VoiceModeler(mock_ollama, mock_loader, test_session)
    result = modeler.learn(["I bring strong analytical skills and a proven track record."])
    assert result["profile_id"] is not None
    assert len(result["profile_id"]) == 32


def test_learn_offline_returns_defaults(mock_loader, test_session):
    offline = MagicMock()
    offline.is_available.return_value = False
    modeler = VoiceModeler(offline, mock_loader, test_session)
    result = modeler.learn(["Some cover letter text."])
    assert isinstance(result["tone_descriptors"], list)


def test_get_or_create_default_returns_profile(mock_loader, test_session):
    offline = MagicMock()
    offline.is_available.return_value = False
    modeler = VoiceModeler(offline, mock_loader, test_session)
    result = modeler.get_or_create_default()
    assert "tone_descriptors" in result
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/unit/test_voice_modeler.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Create `__init__.py`**

Create `backend/services/cover_letter/__init__.py` (empty).

- [ ] **Step 4: Implement voice modeler**

Create `backend/services/cover_letter/voice_modeler.py`:

```python
from __future__ import annotations

import json
import logging
from sqlalchemy.orm import Session

from backend.repositories.resume import WritingProfileRepository

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE = {
    "tone_descriptors": ["professional", "confident", "results-oriented"],
    "structure_patterns": ["hook → value proposition → evidence → call to action"],
    "vocabulary_patterns": {
        "formal_phrases": ["I am excited to", "I bring", "I have demonstrated"],
        "transition_words": ["furthermore", "additionally", "building on this"],
        "avoid": ["I feel", "I think", "I believe"],
    },
    "sample_sentences": [
        "I bring a proven track record of delivering measurable outcomes.",
        "My experience in [field] has equipped me to drive results from day one.",
    ],
}


class VoiceModeler:
    def __init__(self, ollama_client, prompt_loader, session: Session) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader
        self._profile_repo = WritingProfileRepository(session)

    def learn(self, source_texts: list[str]) -> dict:
        profile_data = self._extract_profile(source_texts)
        profile = self._profile_repo.create(
            tone_descriptors=profile_data["tone_descriptors"],
            structure_patterns=profile_data["structure_patterns"],
            vocabulary_patterns=profile_data["vocabulary_patterns"],
            sample_sentences=profile_data["sample_sentences"],
            source_doc_ids=[],
        )
        return {
            "profile_id": profile.id,
            **profile_data,
        }

    def get_or_create_default(self) -> dict:
        existing = self._profile_repo.get_latest()
        if existing:
            return {
                "profile_id": existing.id,
                "tone_descriptors": existing.tone_descriptors,
                "structure_patterns": existing.structure_patterns,
                "vocabulary_patterns": existing.vocabulary_patterns,
                "sample_sentences": existing.sample_sentences,
            }
        return {"profile_id": None, **_DEFAULT_PROFILE}

    def _extract_profile(self, source_texts: list[str]) -> dict:
        if not self._ollama or not self._ollama.is_available():
            return dict(_DEFAULT_PROFILE)
        try:
            prompt_data = self._loader.load("cover_letter/learn_voice")
            combined = "\n\n---\n\n".join(source_texts[:5])[:6000]
            user = prompt_data["user_template"].format(cover_letter_texts=combined)
            raw = self._ollama.generate(
                model=None,
                prompt=user,
                temperature=0.1,
                system=prompt_data["system"],
            )
            data = json.loads(raw)
            return {
                "tone_descriptors": data.get("tone_descriptors", []),
                "structure_patterns": data.get("structure_patterns", []),
                "vocabulary_patterns": data.get("vocabulary_patterns", {}),
                "sample_sentences": data.get("sample_sentences", []),
            }
        except Exception as exc:
            logger.warning("voice_modeler: extraction failed, using defaults: %s", exc)
            return dict(_DEFAULT_PROFILE)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest backend/tests/unit/test_voice_modeler.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/services/cover_letter/ backend/tests/unit/test_voice_modeler.py
git commit -m "feat: add cover letter voice modeler with WritingProfile persistence"
```

---

### Task 9: Cover Letter Generator + DOCX Export

**Files:**
- Create: `backend/services/cover_letter/generator.py`
- Create: `backend/services/cover_letter/docx_exporter.py`
- Create: `backend/tests/unit/test_cover_letter_generator.py`

**Interfaces:**
- Consumes: `EvidenceSelector` (Task 4), `VoiceModeler` (Task 8), `PromptLoader` (Task 1), `OllamaClient`
- Produces:
  - `CoverLetterGenerator(evidence_selector, voice_modeler, ollama_client, prompt_loader).generate(job_description, company, job_title, length_target) -> dict`
    returning `{text, word_count, length_target, requires_approval}`
    - `length_target` values: `"short"` (100 words), `"medium"` (250), `"long"` (400), `"full"` (600)
  - `CoverLetterDOCXExporter().export(text: str, job_title: str, company: str) -> bytes`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/unit/test_cover_letter_generator.py`:

```python
from unittest.mock import MagicMock
import pytest
from backend.services.cover_letter.generator import CoverLetterGenerator, LENGTH_TARGETS


def test_length_targets_defined():
    assert "short" in LENGTH_TARGETS
    assert "medium" in LENGTH_TARGETS
    assert "long" in LENGTH_TARGETS
    assert "full" in LENGTH_TARGETS
    assert LENGTH_TARGETS["short"] == 100
    assert LENGTH_TARGETS["full"] == 600


@pytest.fixture
def mock_selector():
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Led Python migration saving $200K annually", "evidence_id": "b1",
         "experience_id": "exp1", "company": "Acme", "title": "Engineer", "dates": "2022–2024",
         "confidence": "verified"}
    ]
    return sel


@pytest.fixture
def mock_voice():
    vm = MagicMock()
    vm.get_or_create_default.return_value = {
        "profile_id": None,
        "tone_descriptors": ["professional", "confident"],
        "structure_patterns": ["hook → evidence → close"],
        "vocabulary_patterns": {"formal_phrases": ["I am excited"], "transition_words": [], "avoid": []},
        "sample_sentences": ["I bring measurable results."],
    }
    return vm


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Write cover letter.",
        "user_template": (
            "JD: {job_description}\nCompany: {company}\nTitle: {job_title}\n"
            "Industry: {industry}\nLength: {length_target}\nTone: {tone_descriptors}\n"
            "Vocab: {vocabulary_patterns}\nSamples: {sample_sentences}\n"
            "Evidence: {evidence_json}\nKeywords: {keywords}"
        ),
    }
    return loader


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    # Return a 250-word text approximation
    client.generate.return_value = " ".join(["word"] * 250)
    return client


def test_generate_returns_required_keys(mock_selector, mock_voice, mock_loader, mock_ollama):
    gen = CoverLetterGenerator(mock_selector, mock_voice, mock_ollama, mock_loader)
    result = gen.generate("Python engineer role", "Acme Corp", "Engineer", "medium")
    for key in ["text", "word_count", "length_target", "requires_approval"]:
        assert key in result


def test_generate_correct_length_target(mock_selector, mock_voice, mock_loader, mock_ollama):
    gen = CoverLetterGenerator(mock_selector, mock_voice, mock_ollama, mock_loader)
    result = gen.generate("Role", "Co", "Title", "short")
    assert result["length_target"] == "short"


def test_generate_invalid_length_raises(mock_selector, mock_voice, mock_loader, mock_ollama):
    gen = CoverLetterGenerator(mock_selector, mock_voice, mock_ollama, mock_loader)
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate("Role", "Co", "Title", "invalid")


def test_generate_offline_returns_text(mock_selector, mock_voice, mock_loader):
    offline = MagicMock()
    offline.is_available.return_value = False
    gen = CoverLetterGenerator(mock_selector, mock_voice, offline, mock_loader)
    result = gen.generate("Role", "Co", "Title", "medium")
    assert isinstance(result["text"], str)
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/unit/test_cover_letter_generator.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement cover letter generator**

Create `backend/services/cover_letter/generator.py`:

```python
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

LENGTH_TARGETS: dict[str, int] = {
    "short": 100,
    "medium": 250,
    "long": 400,
    "full": 600,
}


class CoverLetterGenerator:
    def __init__(self, evidence_selector, voice_modeler, ollama_client, prompt_loader) -> None:
        self._selector = evidence_selector
        self._voice = voice_modeler
        self._ollama = ollama_client
        self._loader = prompt_loader

    def generate(
        self,
        job_description: str,
        company: str,
        job_title: str,
        length_target: str,
    ) -> dict:
        if length_target not in LENGTH_TARGETS:
            raise ValueError(f"Invalid length_target '{length_target}'. Valid: {list(LENGTH_TARGETS)}")

        target_words = LENGTH_TARGETS[length_target]
        profile = self._voice.get_or_create_default()
        evidence = self._selector.select(job_description, {}, max_bullets=6)
        weak_count = sum(1 for e in evidence if e.get("confidence") == "weak_inference")

        if self._ollama and self._ollama.is_available():
            text = self._llm_generate(job_description, company, job_title, length_target, target_words, profile, evidence)
        else:
            text = self._template_generate(company, job_title, evidence, target_words)

        word_count = len(text.split())
        return {
            "text": text,
            "word_count": word_count,
            "length_target": length_target,
            "requires_approval": weak_count > 0,
        }

    def _llm_generate(
        self,
        job_description: str,
        company: str,
        job_title: str,
        length_target: str,
        target_words: int,
        profile: dict,
        evidence: list[dict],
    ) -> str:
        try:
            prompt_data = self._loader.load("cover_letter/generate")
            evidence_json = json.dumps([
                {"text": e["bullet_text"], "company": e["company"],
                 "title": e["title"], "confidence": e["confidence"]}
                for e in evidence
            ], indent=2)
            user = prompt_data["user_template"].format(
                job_description=job_description[:2000],
                company=company,
                job_title=job_title,
                industry="",
                length_target=target_words,
                tone_descriptors=", ".join(profile.get("tone_descriptors", [])),
                vocabulary_patterns=json.dumps(profile.get("vocabulary_patterns", {})),
                sample_sentences="\n".join(profile.get("sample_sentences", [])),
                evidence_json=evidence_json,
                keywords="",
            )
            return self._ollama.generate(
                model=None,
                prompt=user,
                temperature=0.3,
                system=prompt_data["system"],
            )
        except Exception as exc:
            logger.warning("cl_generator: LLM failed: %s", exc)
            return self._template_generate(company, job_title, evidence, target_words)

    def _template_generate(
        self, company: str, job_title: str, evidence: list[dict], target_words: int
    ) -> str:
        lines = [
            f"Dear Hiring Manager,",
            "",
            f"I am writing to express my interest in the {job_title} position at {company}.",
            "",
        ]
        for e in evidence[:3]:
            lines.append(f"In my previous role as {e.get('title', 'a professional')}, "
                         f"I {e['bullet_text'].lower().lstrip('builledimprovedled ')}.")
        lines += ["", "I look forward to the opportunity to discuss how my experience aligns with your needs.", ""]
        lines.append("Sincerely,")
        return "\n".join(lines)
```

- [ ] **Step 4: Implement cover letter DOCX exporter**

Create `backend/services/cover_letter/docx_exporter.py`:

```python
from __future__ import annotations

import io
import logging
from docx import Document
from docx.shared import Pt

logger = logging.getLogger(__name__)


class CoverLetterDOCXExporter:
    def export(self, text: str, job_title: str, company: str) -> bytes:
        try:
            doc = Document()
            for section in doc.sections:
                section.top_margin = Pt(72)
                section.bottom_margin = Pt(72)
                section.left_margin = Pt(72)
                section.right_margin = Pt(72)
            for line in text.split("\n"):
                doc.add_paragraph(line)
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
        except Exception as exc:
            logger.error("cl_docx_exporter: failed: %s", exc)
            doc = Document()
            doc.add_paragraph(text)
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest backend/tests/unit/test_cover_letter_generator.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add backend/services/cover_letter/generator.py backend/services/cover_letter/docx_exporter.py \
        backend/tests/unit/test_cover_letter_generator.py
git commit -m "feat: add cover letter generator with length variants and DOCX export"
```

---

### Task 10: Cover Letter API Route + Final Coverage Gate

**Files:**
- Create: `backend/api/v1/routes/cover_letter.py`
- Modify: `backend/main.py` — register cover letter router
- Create: `backend/tests/integration/test_cover_letter_api.py`

**Interfaces:**
- Produces:
  - `POST /api/v1/cover-letter/generate` body: `{job_description, company, job_title, length_target}` → `{text, word_count, length_target, requires_approval}`
  - `POST /api/v1/cover-letter/generate/download` → DOCX file
  - `POST /api/v1/cover-letter/learn-voice` body: `{texts: list[str]}` → `{profile_id, tone_descriptors, ...}`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/integration/test_cover_letter_api.py`:

```python
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app):
    return TestClient(app)


def test_generate_cover_letter_returns_text(client):
    with patch("backend.api.v1.routes.cover_letter.OllamaClient") as mock_cls, \
         patch("backend.api.v1.routes.cover_letter.RAGRetriever") as mock_ret_cls, \
         patch("backend.api.v1.routes.cover_letter.Reranker") as mock_rnk_cls:
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post("/api/v1/cover-letter/generate", json={
            "job_description": "Python engineer at Acme",
            "company": "Acme Corp",
            "job_title": "Software Engineer",
            "length_target": "medium",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "word_count" in data
    assert "requires_approval" in data


def test_generate_cover_letter_invalid_length(client):
    resp = client.post("/api/v1/cover-letter/generate", json={
        "job_description": "Python role",
        "company": "Co",
        "job_title": "Dev",
        "length_target": "gigantic",
    })
    assert resp.status_code == 422


def test_learn_voice_returns_profile(client):
    with patch("backend.api.v1.routes.cover_letter.OllamaClient") as mock_cls:
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama

        resp = client.post("/api/v1/cover-letter/learn-voice", json={
            "texts": ["Dear Hiring Manager, I am excited to apply for this role."]
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "tone_descriptors" in data
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m pytest backend/tests/integration/test_cover_letter_api.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or 404.

- [ ] **Step 3: Create cover letter API route**

Create `backend/api/v1/routes/cover_letter.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.services.cover_letter.docx_exporter import CoverLetterDOCXExporter
from backend.services.cover_letter.generator import CoverLetterGenerator, LENGTH_TARGETS
from backend.services.cover_letter.voice_modeler import VoiceModeler
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader
from backend.services.resume.evidence_selector import EvidenceSelector

router = APIRouter(tags=["cover_letter"])

_VALID_LENGTHS = set(LENGTH_TARGETS)


class GenerateCLRequest(BaseModel):
    job_description: str
    company: str
    job_title: str
    length_target: str = "medium"
    application_id: str | None = None


class LearnVoiceRequest(BaseModel):
    texts: list[str]


def _build_generator(settings, session: Session):
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    loader = PromptLoader()
    selector = EvidenceSelector(retriever, reranker)
    voice_modeler = VoiceModeler(ollama, loader, session)
    return CoverLetterGenerator(selector, voice_modeler, ollama, loader), ollama


@router.post("/cover-letter/generate")
def generate_cover_letter(body: GenerateCLRequest, session: Session = Depends(get_session)):
    if body.length_target not in _VALID_LENGTHS:
        raise HTTPException(status_code=422, detail=f"Invalid length_target '{body.length_target}'. Valid: {list(_VALID_LENGTHS)}")
    settings = get_settings()
    gen, _ = _build_generator(settings, session)
    return gen.generate(body.job_description, body.company, body.job_title, body.length_target)


@router.post("/cover-letter/generate/download")
def generate_cover_letter_docx(body: GenerateCLRequest, session: Session = Depends(get_session)):
    if body.length_target not in _VALID_LENGTHS:
        raise HTTPException(status_code=422, detail=f"Invalid length_target '{body.length_target}'.")
    settings = get_settings()
    gen, _ = _build_generator(settings, session)
    result = gen.generate(body.job_description, body.company, body.job_title, body.length_target)
    exporter = CoverLetterDOCXExporter()
    docx_bytes = exporter.export(result["text"], body.job_title, body.company)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=cover_letter.docx"},
    )


@router.post("/cover-letter/learn-voice")
def learn_voice(body: LearnVoiceRequest, session: Session = Depends(get_session)):
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    loader = PromptLoader()
    modeler = VoiceModeler(ollama, loader, session)
    return modeler.learn(body.texts)
```

- [ ] **Step 4: Register cover letter router in main.py**

Read `backend/main.py`, add:

```python
from backend.api.v1.routes.cover_letter import router as cover_letter_router
# ...
app.include_router(cover_letter_router, prefix="/api/v1")
```

- [ ] **Step 5: Run integration tests**

```bash
python -m pytest backend/tests/integration/test_cover_letter_api.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 6: Run full suite and coverage gate**

```bash
source .venv/bin/activate
python -m pytest backend/tests/ -v --cov=backend --cov-report=term-missing 2>&1 | tail -20
```

Expected: ≥90% total coverage; all tests PASSED.

- [ ] **Step 7: Commit**

```bash
git add backend/api/v1/routes/cover_letter.py backend/main.py \
        backend/tests/integration/test_cover_letter_api.py
git commit -m "feat: add cover letter API routes (generate, download, learn-voice) and Phase 3 coverage gate"
```

---

## Self-Review

### Spec Coverage Check

| Spec Item | Task |
|-----------|------|
| Resume Engine — one-page enforced | Task 5 (`page_count=1` in DB record, LLM instructed) |
| Resume templates: software, AI, product, consulting, data_analytics, healthcare | Task 4 (all 6 defined) |
| ATS-optimized generation pipeline | Tasks 2+3+5 (keyword extraction → scoring → generator uses score) |
| Evidence-based bullet generation only | Tasks 4+5 (EvidenceSelector queries RAG; no invented content) |
| Cover letter: 100/250/400/full-page formats | Task 9 (LENGTH_TARGETS dict) |
| Voice modeling from historical cover letters | Task 8 (VoiceModeler.learn()) |
| ATS keyword matching | Task 2+3 |
| ATS skill matching | Task 3 (_keyword_score method) |
| ATS industry alignment | Task 3 (industry_score in LLM scoring) |
| ATS experience matching | Task 3 (experience_score in LLM scoring) |
| ATS score + explanation | Task 3 (explanation field in output) |
| DOCX generation via python-docx | Tasks 6+9 |
| Template rendering system | Task 4 (templates.py) |
| Versioned prompts | Task 1 (version field in YAML) |
| Reusable prompt templates | Task 1 (user_template with {placeholders}) |
| Structured inputs/outputs | Task 1 (YAML schema; Task 3 Pydantic models) |
| Confidence system in output | Tasks 5+6 (weak_inference flagged in DOCX and requires_approval) |
| Weak inference requires user approval | Tasks 5+9 (`requires_approval` flag) |
| No hallucinated metrics/employers/projects | Tasks 4+5 (EvidenceSelector, LLM system prompt) |
| Prompt library functional | Task 1 |
| Basic evaluation tests | All tasks (unit + integration) |

### Placeholder Scan

No TBD, "implement later", or "similar to Task N" patterns present.

### Type Consistency

- `EvidenceSelector.select() -> list[dict]` — bullet dict shape consistent across Tasks 4, 5, 8, 9
- `ATSScorer.score() -> dict` — consistent 8-key shape across Tasks 3, 5, 7
- `ResumeGenerator.generate() -> dict` — consistent 5-key shape across Tasks 5, 7
- `CoverLetterGenerator.generate() -> dict` — consistent 4-key shape across Tasks 9, 10
- `PromptLoader.load(name) -> dict` — consistent 3-key shape across all tasks
