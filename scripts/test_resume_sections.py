#!/usr/bin/env python
"""
scripts/test_resume_sections.py

Generate, score, and rank resume-quality bullets for Experience, Projects,
and Activities, then simulate layout selection with Experience taking priority.

Sources:
  Experience  — .static_files/profile/cv.txt + experience-bank.md (verified)
  Projects    — GitHub repos synthesized into structured bullets (strong_inference)
  Activities  — Leadership / team-building bullets from experience-bank.md

Scoring: Phase 8.1 BulletScorer (5 dimensions)
Layout:  Experience fills first, then Projects, then Activities.

Does NOT require Ollama or database — fully local + rule-based.

Usage:
    python scripts/test_resume_sections.py
    python scripts/test_resume_sections.py --no-github
    python scripts/test_resume_sections.py --jd "data analyst SQL Python..."
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.resume.bullet_quality import BulletQualityChecker
from backend.services.resume.bullet_rewriter import BulletRewriter, ACTION_VERBS
from backend.services.resume.bullet_scorer import BulletScorer

_QUALITY = BulletQualityChecker()
_SEVERITY_ICON = {"error": "🚫", "warning": "⚠️ ", "suggestion": "💡"}

# ── Static file paths ─────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
_CV_PATH = _ROOT / ".static_files/profile/cv.txt"

# ── Scoring keywords (broad analytics/data stack — override with --jd) ───────

DEFAULT_KEYWORDS = [
    # Core technical skills (Andrew's stack)
    "Python", "SQL", "ETL", "pipeline", "automation", "analytics", "data",
    "visualization", "GCP", "API", "OCR", "PDF", "analysis", "reporting",
    # Litigation / forensic domain
    "forensic", "compliance", "litigation", "damages", "fraud", "financial",
    "audit", "investigation", "HIPAA", "OFAC", "privacy",
    # Software / AI project stack
    "LLM", "AI", "RAG", "agent", "TypeScript", "React", "FastAPI",
]

# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Bullet:
    text: str
    section: str        # "experience" | "projects" | "activities"
    source: str         # engagement name, repo name, etc.
    confidence: str     # "verified" | "strong_inference"
    score: float = 0.0
    rewritten: str = ""
    dim_scores: dict[str, float] = field(default_factory=dict)


# ── EXPERIENCE: cv.txt paragraph parsing ─────────────────────────────────────

# Each heading maps to text that appears in cv.txt; order matters for boundary detection.
_CV_ENGAGEMENTS = [
    ("HIPAA / CIPA / VPPA Web Technology Compliance / Litigation", "AdTech / Privacy"),
    ("IOLA Compliance", "IOLA Fraud"),
    ("Grocery Store M&A Civil Damages Litigation", "Grocery M&A"),
    ("PPP Loan Misappropriation Litigation", "PPP Fraud"),
    ("Stock Manipulation Dispute Litigation", "Stock Manipulation"),
    ("IP Infringement Litigation", "IP Infringement"),
    ("Gold Trading Fraud & Damages Litigation", "Gold Fraud"),
    ("Terrorist Financing & OFAC Compliance Litigation", "Terrorist Financing / OFAC"),
]


def _split_paragraph(paragraph: str) -> list[str]:
    """Split one narrative paragraph into individual sentence candidates."""
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z])", paragraph.strip())
    out = []
    for sent in raw:
        sent = sent.strip().rstrip(".")
        if len(sent) < 35:
            continue
        # Trim very long sentences to last natural break before 200 chars
        if len(sent) > 200:
            sent = sent[:200].rsplit(" ", 1)[0]
        out.append(sent)
    return out


def parse_cv_experience(cv_path: Path) -> list[Bullet]:
    """Extract sentence-level bullet candidates from each cv.txt engagement paragraph."""
    if not cv_path.exists():
        print(f"  Warning: {cv_path} not found")
        return []

    text = cv_path.read_text(encoding="utf-8")
    bullets: list[Bullet] = []

    for i, (heading, label) in enumerate(_CV_ENGAGEMENTS):
        pos = text.find(heading)
        if pos == -1:
            continue
        after = text[pos + len(heading):].lstrip()
        # Paragraph ends at the next engagement heading or end of file
        end = len(after)
        for j, (other_heading, _) in enumerate(_CV_ENGAGEMENTS):
            if j == i:
                continue
            p = after.find(other_heading)
            if p != -1 and p < end:
                end = p
        paragraph = after[:end].strip()

        for sent in _split_paragraph(paragraph):
            bullets.append(Bullet(
                text=sent,
                section="experience",
                source=label,
                confidence="verified",
            ))

    return bullets


# ── EXPERIENCE: verified high-signal facts from experience-bank.md ────────────
#
# These represent the career-level metrics and team-building story that don't
# appear verbatim in the cv.txt case narratives.

_BANK_BULLETS: list[tuple[str, str]] = [
    (
        "Built Python ETL pipeline and library from scratch that became a core revenue-generating workstream, driving $3M+ revenue across 150+ client engagements",
        "Pipeline / Revenue",
    ),
    (
        "Delivered digital privacy analytics 30x faster than prior manual workflows, scaling the practice from zero to a primary firm revenue driver",
        "Pipeline / Revenue",
    ),
    (
        "Independently identified the digital privacy analytics opportunity and overcame initial leadership skepticism to establish the workstream",
        "Leadership / Ownership",
    ),
    (
        "Recruited, hired, and managed interns within 5 months of joining; maintained 100% offer, return, and retention rate across all cycles",
        "Team Building",
    ),
    (
        "Led Chicago Analytics & Data Strategy team composed entirely of former interns, demonstrating unusual ownership depth for sub-4-year tenure",
        "Team Building",
    ),
    (
        "Partnered with 30+ hospital systems — including Rush, Kaiser Permanente, Dana-Farber, and Mount Sinai — on healthcare digital-privacy litigation across Epic and Cerner EHR environments",
        "Healthcare / EHR",
    ),
    (
        "Contributed analysis driving vendor-level patient-portal deployment changes at Cerner across hospital network configurations",
        "Healthcare / EHR",
    ),
]


def get_bank_bullets() -> list[Bullet]:
    return [
        Bullet(text=t, section="experience", source=s, confidence="verified")
        for t, s in _BANK_BULLETS
    ]


# ── ACTIVITIES: leadership / team-building highlights ─────────────────────────

_ACTIVITY_BULLETS: list[tuple[str, str]] = [
    (
        "Led full recruiting pipeline for Chicago Analytics team, sourcing from Northwestern University and converting 100% of intern cohort to full-time hires",
        "Recruiting / Team Building",
    ),
    (
        "Mentored junior analysts across forensic accounting, Python automation, and data visualization; all mentees retained or promoted",
        "Mentorship",
    ),
    (
        "Built analytics team from the ground up within first 5 months at firm, managing hiring, onboarding, and technical development",
        "Team Building",
    ),
]


def get_activity_bullets() -> list[Bullet]:
    return [
        Bullet(text=t, section="activities", source=s, confidence="verified")
        for t, s in _ACTIVITY_BULLETS
    ]


# ── PROJECTS: GitHub repo bullet synthesis ────────────────────────────────────

def _gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=True)
    return result.stdout


def fetch_repos(username: str) -> list[dict]:
    raw = _gh(
        "repo", "list", username,
        "--json", "name,description,primaryLanguage,stargazerCount,url",
        "--limit", "50",
    )
    return json.loads(raw)


def fetch_readme(username: str, repo_name: str) -> str:
    try:
        import base64
        b64 = _gh("api", f"repos/{username}/{repo_name}/readme", "--jq", ".content")
        return base64.b64decode(b64.strip()).decode("utf-8", errors="ignore")[:6000]
    except subprocess.CalledProcessError:
        return ""


_TECH_RE = re.compile(
    r"\b(Python|TypeScript|JavaScript|React|Next\.js|Supabase|PostgreSQL|SQLite|"
    r"FastAPI|Tauri|ChromaDB|Ollama|dbt|DuckDB|GitHub\s*Actions|Playwright|"
    r"Claude\s*(?:API|SDK)?|LLM|RAG|Alembic|SQLAlchemy|TailwindCSS|Pydantic)\b",
    re.IGNORECASE,
)

_README_ACTION_RE = re.compile(
    r"\b(automates?|generates?|processes?|enables?|powers?|integrates?|"
    r"reduces?|tracks?|serves?|aggregates?)\b",
    re.IGNORECASE,
)


def synthesize_project_bullets(repo: dict, readme: str) -> list[str]:
    """
    Synthesize full-sentence resume bullets from structured repo metadata.

    Strategy: [action verb] + [functional description] + using [tech] + ([quant])
    Avoids extracting raw README prose (noise); derives bullets from metadata.
    """
    bullets: list[str] = []
    name = repo.get("name", "")
    desc = (repo.get("description") or "").strip()
    lang_obj = repo.get("primaryLanguage")
    lang = (lang_obj.get("name", "") if isinstance(lang_obj, dict) else "")

    # Tech stack from README (deduplicated, order-preserving)
    tech_found = list(dict.fromkeys(_TECH_RE.findall(readme)))
    # Normalise casing of language match
    if lang and not any(lang.lower() == t.lower() for t in tech_found):
        tech_found.insert(0, lang)
    stack_str = " + ".join(tech_found[:4]) if tech_found else lang

    # Numbers from README (filter out 0/1/2 and large version-like numbers)
    numbers = [n for n in re.findall(r"\b(\d+)\b", readme[:3000]) if 3 <= int(n) <= 500]

    # Clean description: remove articles, verb prefix, "is a/an" clause
    core = desc.rstrip(".")
    if core:
        # Strip leading article ("A", "An", "The")
        words = core.split()
        if words and words[0].lower() in ("a", "an", "the"):
            core = " ".join(words[1:])
        # Strip leading action verb to avoid "Built Built ..."
        words = core.split()
        if words and words[0].lower().rstrip(".,;:") in ACTION_VERBS:
            core = " ".join(words[1:])
        # Trim after "is a/an" (e.g., "ACOS is an app for..." → "ACOS")
        core = re.split(r"\s+is\s+(?:a|an)\s+", core, maxsplit=1)[0].strip()
        # Trim to a single clause if still long
        if len(core) > 110:
            core = core[:110].rsplit(" ", 1)[0]
    if not core:
        core = name.replace("-", " ").replace("_", " ").title()

    # --- Bullet 1: primary synthesis ---
    if core and stack_str:
        quant = f" ({int(numbers[0])}+ items)" if numbers else ""
        # Avoid double "using" when description already names the stack
        using_clause = "" if "using" in core.lower() else f" using {stack_str}"
        b1 = f"Built {core}{using_clause}{quant}"
        if len(b1) <= 176:
            bullets.append(b1)

    # --- Bullet 2: README achievement sentence (action + quant required) ---
    prose_lines = [
        l.strip() for l in readme.splitlines()
        if l.strip()
        and not l.strip().startswith(("#", ">", "|", "-", "*", "```", "<", "http"))
        and not re.match(r"^\s*\d+\.", l.strip())
    ]
    prose_text = " ".join(prose_lines[:60])
    for raw in re.split(r"(?<=[.!?])\s+", prose_text):
        sent = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", raw)
        sent = re.sub(r"`[^`]*`", "", sent).strip()
        if (
            40 <= len(sent) <= 160
            and _README_ACTION_RE.search(sent)
            and re.search(r"\d", sent)
        ):
            bullets.append(sent)
            break  # one README-derived bullet per repo

    return bullets[:3]  # cap at 3 per repo


def get_project_bullets(username: str) -> list[Bullet]:
    try:
        repos = fetch_repos(username)
    except Exception as exc:
        print(f"  Warning: GitHub fetch failed ({exc})")
        return []

    bullets: list[Bullet] = []
    for repo in repos:
        name = repo["name"]
        readme = fetch_readme(username, name)
        status = f"({len(readme)} chars)" if readme else "(no README)"
        print(f"  {name}: {status}")
        for text in synthesize_project_bullets(repo, readme):
            bullets.append(Bullet(
                text=text,
                section="projects",
                source=name,
                confidence="strong_inference",
            ))
    return bullets


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_bullets(
    bullets: list[Bullet],
    keywords: list[str],
    relevance_score: float = 0.7,
) -> list[Bullet]:
    """Score + rewrite each bullet independently; return sorted descending."""
    scorer = BulletScorer()
    rewriter = BulletRewriter()

    for b in bullets:
        b.rewritten = rewriter.compress(b.text)
        dims = scorer.score_dimensions(
            {"bullet_text": b.rewritten},
            keywords,
            relevance_score=relevance_score,
        )
        b.score = round(sum(dims.values()), 3)
        b.dim_scores = {k: round(v, 3) for k, v in dims.items()}

    return sorted(bullets, key=lambda x: x.score, reverse=True)


# ── Layout budget allocation ──────────────────────────────────────────────────

# Line estimates for a standard single-column resume
_FIXED_LINES = 12      # name/contact header + education + skills section
_SEC_HEADER = 2        # "EXPERIENCE" heading + rule
_ROLE_HEADER = 2       # company + title/date line
_BULLET_LINES = 2      # avg lines per bullet at 88 chars/line
_MAX_PAGE_LINES = 60


def select_for_resume(
    experience: list[Bullet],
    projects: list[Bullet],
    activities: list[Bullet],
) -> tuple[list[Bullet], list[Bullet], list[Bullet]]:
    """
    Fill Experience first, then Projects, then Activities.
    Returns (selected_exp, selected_proj, selected_act).
    """
    remaining = _MAX_PAGE_LINES - _FIXED_LINES

    # Experience
    exp_avail = remaining - _SEC_HEADER - _ROLE_HEADER
    exp_max = max(0, exp_avail // _BULLET_LINES)
    sel_exp = experience[:min(exp_max, 12)]
    remaining -= _SEC_HEADER + _ROLE_HEADER + len(sel_exp) * _BULLET_LINES

    # Projects
    proj_avail = remaining - _SEC_HEADER
    proj_max = max(0, proj_avail // _BULLET_LINES)
    sel_proj = projects[:min(proj_max, 6)]
    remaining -= _SEC_HEADER + len(sel_proj) * _BULLET_LINES

    # Activities
    act_avail = remaining - _SEC_HEADER
    act_max = max(0, act_avail // _BULLET_LINES)
    sel_act = activities[:min(act_max, 4)]

    return sel_exp, sel_proj, sel_act


# ── Reporting ─────────────────────────────────────────────────────────────────

_W = BulletScorer.WEIGHTS
_BAR = 18


def _bar(score: float, cap: float = 1.0) -> str:
    pct = min(1.0, score / cap) if cap > 0 else 0.0
    f = int(pct * _BAR)
    return "█" * f + "░" * (_BAR - f)


def _label(score: float) -> str:
    if score >= 0.70:
        return "✅  STRONG"
    if score >= 0.45:
        return "🟡  FAIR  "
    return "🔴  WEAK  "


def _print_bullet(b: Bullet, rank: int, selected: bool) -> None:
    star = "★" if selected else " "
    print(f"\n  {star} #{rank:02d}  {_label(b.score)}  {_bar(b.score)}  {b.score:.3f}  [{b.source}]")
    if b.rewritten != b.text:
        print(f"      ORIGINAL : {b.text[:105]}")
        print(f"      REWRITTEN: {b.rewritten[:105]}")
    else:
        print(f"      {b.rewritten[:110]}")
    dim_line = "  ".join(
        f"{k[:3].upper()}:{b.dim_scores.get(k, 0):.2f}/{_W[k]:.2f}"
        for k in ["impact", "quantification", "keyword", "leadership", "uniqueness"]
    )
    print(f"      dims: {dim_line}")
    violations = _QUALITY.check(b.rewritten)
    errors_warnings = [v for v in violations if v.severity in ("error", "warning")]
    if errors_warnings:
        for v in errors_warnings:
            print(f"      {_SEVERITY_ICON[v.severity]} [{v.code}] {v.message[:80]}")


def print_report(
    exp_all: list[Bullet],
    proj_all: list[Bullet],
    act_all: list[Bullet],
    sel_exp: list[Bullet],
    sel_proj: list[Bullet],
    sel_act: list[Bullet],
) -> None:
    sel_exp_set = {b.text for b in sel_exp}
    sel_proj_set = {b.text for b in sel_proj}
    sel_act_set = {b.text for b in sel_act}

    print("\n" + "=" * 80)
    print("  RESUME BULLET REPORT  —  Experience / Projects / Activities")
    print("  Phase 8.1 BulletScorer  |  5 dimensions  |  ★ = selected for resume")
    print("=" * 80)

    # ── EXPERIENCE ───────────────────────────────────────────────────────────
    print(f"\n{'─' * 80}")
    strong_e = sum(1 for b in exp_all if b.score >= 0.70)
    fair_e   = sum(1 for b in exp_all if 0.45 <= b.score < 0.70)
    print(f"  EXPERIENCE — Secretariat Advisors  "
          f"({len(exp_all)} candidates  ✅{strong_e}  🟡{fair_e}  "
          f"|  {len(sel_exp)} selected for resume)")
    print(f"{'─' * 80}")

    for i, b in enumerate(exp_all, 1):
        _print_bullet(b, i, b.text in sel_exp_set)

    # ── PROJECTS ─────────────────────────────────────────────────────────────
    print(f"\n{'─' * 80}")
    strong_p = sum(1 for b in proj_all if b.score >= 0.70)
    fair_p   = sum(1 for b in proj_all if 0.45 <= b.score < 0.70)
    print(f"  PROJECTS — GitHub repos  "
          f"({len(proj_all)} candidates  ✅{strong_p}  🟡{fair_p}  "
          f"|  {len(sel_proj)} selected for resume)")
    print(f"{'─' * 80}")

    if not proj_all:
        print("\n  (no project candidates — run without --no-github to fetch repos)")
    for i, b in enumerate(proj_all, 1):
        _print_bullet(b, i, b.text in sel_proj_set)

    # ── ACTIVITIES ────────────────────────────────────────────────────────────
    print(f"\n{'─' * 80}")
    print(f"  ACTIVITIES / LEADERSHIP  "
          f"({len(act_all)} candidates  |  {len(sel_act)} selected)")
    print(f"{'─' * 80}")

    for i, b in enumerate(act_all, 1):
        _print_bullet(b, i, b.text in sel_act_set)

    # ── RESUME PREVIEW ───────────────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("  RESUME PREVIEW  (selected bullets only)")
    print(f"{'=' * 80}")

    print(f"\n  EXPERIENCE — Secretariat Advisors | Senior Associate | Sept 2022–Present")
    for b in sel_exp:
        print(f"  • {b.rewritten[:110]}")

    if sel_proj:
        print(f"\n  PROJECTS")
        for b in sel_proj:
            print(f"  • {b.rewritten[:100]}  [{b.source}]")

    if sel_act:
        print(f"\n  ACTIVITIES / LEADERSHIP")
        for b in sel_act:
            print(f"  • {b.rewritten[:110]}")

    # ── SUMMARY ──────────────────────────────────────────────────────────────
    all_sel = sel_exp + sel_proj + sel_act
    all_cands = exp_all + proj_all + act_all
    s = sum(1 for b in all_sel if b.score >= 0.70)
    f = sum(1 for b in all_sel if 0.45 <= b.score < 0.70)
    w = sum(1 for b in all_sel if b.score < 0.45)
    avg = sum(b.score for b in all_cands) / len(all_cands) if all_cands else 0

    print(f"\n  Selected: {len(all_sel)} bullets  |  ✅ Strong: {s}  🟡 Fair: {f}  🔴 Weak: {w}")
    print(f"  Total candidates: {len(all_cands)}  |  Pool avg score: {avg:.3f}")
    print(f"  Layout: {len(sel_exp)} exp + {len(sel_proj)} proj + {len(sel_act)} act bullets\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score resume bullets for Experience, Projects, Activities"
    )
    parser.add_argument("--username", default="andrew-nguyen-9")
    parser.add_argument("--jd", default="", help="Job description text for keyword extraction")
    parser.add_argument("--no-github", action="store_true", help="Skip GitHub fetching")
    args = parser.parse_args()

    keywords = list(DEFAULT_KEYWORDS)
    if args.jd:
        stopwords = {"with", "that", "this", "from", "have", "will", "your", "their"}
        extra = [w.strip(".,;:()") for w in args.jd.split() if len(w) > 4 and w.lower() not in stopwords]
        keywords = list(dict.fromkeys(keywords + extra))

    # 1. Experience bullets
    print("Loading experience data from static profile files…")
    exp_bullets = parse_cv_experience(_CV_PATH) + get_bank_bullets()
    print(f"  {len(exp_bullets)} experience candidates extracted")

    # 2. Project bullets
    proj_bullets: list[Bullet] = []
    if not args.no_github:
        print(f"\nFetching GitHub repos for @{args.username}…")
        proj_bullets = get_project_bullets(args.username)
        print(f"  {len(proj_bullets)} project candidates generated")

    # 3. Activity bullets
    act_bullets = get_activity_bullets()

    # 4. Score independently (no cross-bullet uniqueness in test mode)
    print("\nScoring all bullets…")
    exp_scored  = score_bullets(exp_bullets,  keywords, relevance_score=0.75)
    proj_scored = score_bullets(proj_bullets, keywords, relevance_score=0.60)
    act_scored  = score_bullets(act_bullets,  keywords, relevance_score=0.65)

    # 5. Layout selection (Experience first)
    sel_exp, sel_proj, sel_act = select_for_resume(exp_scored, proj_scored, act_scored)

    # 6. Report
    print_report(exp_scored, proj_scored, act_scored, sel_exp, sel_proj, sel_act)


if __name__ == "__main__":
    main()
