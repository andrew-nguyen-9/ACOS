#!/usr/bin/env python
"""
Test harness: fetch GitHub repos → generate project bullets → score + rewrite via Phase 8.1 pipeline.

Usage:
    python scripts/test_github_bullets.py [--username andrew-nguyen-9] [--jd "..."]

Requires: gh CLI authenticated (gh auth login).
Does NOT require Ollama — scoring and rewriting are fully local rule-based.
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

from backend.services.resume.bullet_rewriter import BulletRewriter, ACTION_VERBS
from backend.services.resume.bullet_scorer import BulletScorer

# ── Broad tech/product keywords used when no JD is supplied ─────────────────
DEFAULT_KEYWORDS = [
    "Python", "TypeScript", "React", "Next.js", "FastAPI", "Supabase", "PostgreSQL",
    "LLM", "AI", "ETL", "pipeline", "automation", "API", "analytics", "RAG",
    "GitHub Actions", "data", "full-stack", "backend", "frontend", "dbt", "DuckDB",
    "machine learning", "agent", "workflow", "platform", "dashboard",
]

# Minimum score to include a bullet in the output (0–1 scale)
_SCORE_THRESHOLD = 0.05


@dataclass
class BulletResult:
    repo: str
    original: str
    rewritten: str
    score_before: float
    score_after: float
    dim_scores: dict[str, float] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    suggestion: str = ""


# ── GitHub data fetchers ─────────────────────────────────────────────────────

def _gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=True)
    return result.stdout


def fetch_repos(username: str) -> list[dict]:
    raw = _gh(
        "repo", "list", username,
        "--json", "name,description,primaryLanguage,stargazerCount,forkCount,pushedAt,url",
        "--limit", "50",
    )
    return json.loads(raw)


def fetch_readme(username: str, repo_name: str) -> str:
    try:
        b64 = _gh("api", f"repos/{username}/{repo_name}/readme", "--jq", ".content")
        import base64
        return base64.b64decode(b64.strip()).decode("utf-8", errors="ignore")
    except subprocess.CalledProcessError:
        return ""


# ── Bullet candidate generation ───────────────────────────────────────────────

_NOISE_LINE = re.compile(
    r"^(\s*[#>\|\-\*`]"          # markdown headings/blockquotes/tables/lists/code
    r"|```"                       # code fences
    r"|\s*\d+\."                  # numbered lists
    r"|https?://"                 # bare URLs
    r"|cd |npm |pip |yarn |git "  # shell commands
    r"|<[a-z])"                   # HTML tags
)


def _prose_lines(text: str) -> list[str]:
    """Return only prose lines from markdown — strips code, tables, lists, headings."""
    lines = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        if _NOISE_LINE.match(stripped):
            continue
        lines.append(stripped)
    return lines


def _clean(text: str) -> str:
    """Strip markdown links, backticks, and extra whitespace."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [text](url) → text
    text = re.sub(r"`[^`]+`", "", text)                     # `code` → ""
    text = re.sub(r"[#*_>|]", "", text)                     # markdown chars
    return re.sub(r"\s{2,}", " ", text).strip()


def _good_candidate(text: str) -> bool:
    """True if text looks like a single-sentence achievement statement."""
    if len(text) < 30 or len(text) > 200:
        return False
    # Must contain a verb
    if not re.search(r"\b\w+ed\b|\b\w+s\b|\b\w+ing\b", text, re.IGNORECASE):
        return False
    # Reject lines that look like partial titles or nav items
    if text.count(":") > 2 or text.count("→") > 1:
        return False
    return True


def candidates_from_repo(repo: dict, readme: str) -> list[str]:
    """Generate bullet text candidates from a repo dict + its README."""
    bullets: list[str] = []
    lang = (repo.get("primaryLanguage") or {}).get("name", "") if isinstance(repo.get("primaryLanguage"), dict) else ""
    stars = repo.get("stargazerCount", 0)
    desc = (repo.get("description") or "").strip()
    name = repo.get("name", "")

    # 1. Synthesized template bullet from structured metadata
    if desc:
        # Build a tight candidate using actual metadata
        parts = [desc.rstrip(".")]
        if lang:
            if lang.lower() not in desc.lower():
                parts.append(f"using {lang}")
        if stars and stars > 0:
            parts.append(f"({stars} ★)")
        template = " ".join(parts)
        if len(template) <= 200:
            bullets.append(template)

    # 2. README prose sentences with achievement/tech signal
    action_signal = re.compile(
        r"\b(built|designed|automated|created|deployed|launched|developed|implemented|"
        r"architected|generated|scaled|integrated|reduced|improved|serves|powers|"
        r"aggregates|processes|synthesized|combines|leverages|enables)\b",
        re.IGNORECASE,
    )
    tech_signal = re.compile(
        r"\b(python|typescript|react|next\.?js|fastapi|supabase|postgres|llm|ai|etl|"
        r"api|pipeline|dbt|duckdb|chromadb|ollama|github\s+actions|rag|supabase|vercel)\b",
        re.IGNORECASE,
    )
    quant_signal = re.compile(r"\d+")

    prose = " ".join(_prose_lines(readme[:8000]))
    sentences = re.split(r"(?<=[.!?])\s+", prose)

    for raw in sentences:
        sent = _clean(raw).strip()
        if not _good_candidate(sent):
            continue
        has_action = bool(action_signal.search(sent))
        has_tech = bool(tech_signal.search(sent))
        has_quant = bool(quant_signal.search(sent))
        # Require at least two of three signals for inclusion
        if sum([has_action, has_tech, has_quant]) >= 2:
            bullets.append(sent)

    # 3. Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for b in bullets:
        key = re.sub(r"\s+", " ", b.lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(b)
    return unique[:8]  # cap per repo


# ── Scoring + rewriting ───────────────────────────────────────────────────────

def _check_issues(rewritten: str) -> list[str]:
    """Flag obvious quality issues."""
    issues = []
    first = rewritten.split()[0].lower().rstrip(".,;:") if rewritten.split() else ""
    if first not in ACTION_VERBS:
        issues.append(f"❌  no action verb (starts with '{first}')")
    if len(rewritten) > 176:
        issues.append(f"⚠️  too long ({len(rewritten)} chars — split into 2 bullets)")
    if not re.search(r"\d", rewritten):
        issues.append("⚠️  no quantification — add a number ($, %, count, time)")
    return issues


def _suggest_strong(repo: dict, readme: str) -> str:
    """Generate a rule-based 'strong' version of a bullet from repo metadata.

    Shows what the bullet WOULD look like with quantification added.
    """
    name = repo.get("name", "")
    desc = (repo.get("description") or "").strip()
    lang = (repo.get("primaryLanguage") or {}).get("name", "") if isinstance(repo.get("primaryLanguage"), dict) else ""

    # Extract tech stack from README (first 3 mentions)
    tech = re.findall(
        r"\b(Python|TypeScript|Next\.js|Supabase|PostgreSQL|dbt|DuckDB|FastAPI|"
        r"GitHub Actions|ChromaDB|Ollama|React|Tauri|Claude API)\b",
        readme[:4000],
    )
    tech_unique = list(dict.fromkeys(tech))[:4]  # first 4 unique, order-preserving

    # Extract any numbers from README (room counts, festival counts, module counts, etc.)
    numbers = re.findall(r"\b(\d+)\b", readme[:3000])
    interesting_numbers = [n for n in numbers if 2 <= int(n) <= 200][:3]

    # Build the suggestion
    verb = "Built"
    core = desc.rstrip(".")
    if not core:
        core = f"{name.replace('-', ' ').title()} platform"

    # Strip leading action verb from description to avoid double-prefixing
    first_word = core.split()[0].lower().rstrip(".,;:") if core.split() else ""
    if first_word in ACTION_VERBS:
        core = " ".join(core.split()[1:])

    # Trim long descriptions to one clause
    if len(core) > 120:
        core = core[:120].rsplit(" ", 1)[0]

    stack_str = f" using {' + '.join(tech_unique)}" if tech_unique else (f" using {lang}" if lang else "")
    num_str = f" ({interesting_numbers[0]}+ items)" if interesting_numbers else ""

    suggestion = f"{verb} {core}{stack_str}{num_str}"

    # If still no numbers, add a placeholder prompt
    if not re.search(r"\d", suggestion):
        suggestion += "  ← add metric: users / requests / % improvement / hours saved"

    return suggestion[:200]


def score_and_rewrite(
    repos: list[dict],
    readmes: dict[str, str],
    keywords: list[str],
) -> list[BulletResult]:
    scorer = BulletScorer()
    rewriter = BulletRewriter()
    results: list[BulletResult] = []

    for repo in repos:
        name = repo["name"]
        readme = readmes.get(name, "")
        raw_candidates = candidates_from_repo(repo, readme)
        if not raw_candidates:
            continue

        bullet_dicts = [{"bullet_text": c, "confidence": "strong_inference"} for c in raw_candidates]
        scored = scorer.score_many(bullet_dicts, keywords)

        for b in scored:
            if b["score"] < _SCORE_THRESHOLD:
                continue
            original = b["bullet_text"]
            rewritten = rewriter.compress(original)
            dims = scorer.score_dimensions(
                {"bullet_text": rewritten, "confidence": "strong_inference"},
                keywords,
                relevance_score=b["score"],
            )
            score_after = sum(dims.values())
            results.append(BulletResult(
                repo=name,
                original=original,
                rewritten=rewritten,
                score_before=round(b["score"], 3),
                score_after=round(score_after, 3),
                dim_scores={k: round(v, 3) for k, v in dims.items()},
                issues=_check_issues(rewritten),
                suggestion=_suggest_strong(repo, readme),
            ))

    return results


# ── Reporting ─────────────────────────────────────────────────────────────────

_BAR_WIDTH = 20


def _bar(score: float) -> str:
    filled = int(score * _BAR_WIDTH)
    return "█" * filled + "░" * (_BAR_WIDTH - filled)


def _score_label(score: float) -> str:
    if score >= 0.7:
        return "✅  STRONG"
    if score >= 0.45:
        return "🟡  FAIR"
    return "🔴  WEAK"


def _dim_bar(score: float, weight: float) -> str:
    """Mini bar showing earned vs possible for one dimension."""
    possible = weight
    pct = score / possible if possible > 0 else 0
    filled = int(pct * 8)
    return "█" * filled + "░" * (8 - filled)


def print_report(results: list[BulletResult]) -> None:
    if not results:
        print("No bullet candidates generated.")
        return

    # Group by repo
    by_repo: dict[str, list[BulletResult]] = {}
    for r in results:
        by_repo.setdefault(r.repo, []).append(r)

    print("\n" + "=" * 80)
    print("  GITHUB PROJECT BULLET REPORT — Phase 8.1 Pipeline")
    print("=" * 80)

    total = len(results)
    strong = sum(1 for r in results if r.score_after >= 0.70)
    fair = sum(1 for r in results if 0.45 <= r.score_after < 0.70)
    weak = sum(1 for r in results if r.score_after < 0.45)

    print(f"\n  {total} candidates across {len(by_repo)} repos")
    print(f"  ✅ Strong (≥0.70): {strong}  🟡 Fair (0.45–0.70): {fair}  🔴 Weak (<0.45): {weak}\n")

    weights = BulletScorer.WEIGHTS

    for repo_name, bullets in by_repo.items():
        best = sorted(bullets, key=lambda x: x.score_after, reverse=True)[0]
        label = _score_label(best.score_after)

        print(f"\n{'─' * 80}")
        print(f"  📦  {repo_name}   {label}  {_bar(best.score_after)}  {best.score_after:.3f}")
        print(f"{'─' * 80}")

        # Show best candidate only (most informative)
        b = best
        if b.original != b.rewritten:
            print(f"  ORIGINAL:  {b.original[:105]}")
            print(f"  REWRITTEN: {b.rewritten[:105]}")
        else:
            print(f"  BULLET:    {b.original[:105]}")

        # Per-dimension breakdown
        print()
        print("  DIMENSION BREAKDOWN")
        dim_labels = {
            "impact":         f"Impact       ×{weights['impact']:.2f}",
            "quantification": f"Quantif.     ×{weights['quantification']:.2f}",
            "keyword":        f"Keyword      ×{weights['keyword']:.2f}",
            "leadership":     f"Leadership   ×{weights['leadership']:.2f}",
            "uniqueness":     f"Uniqueness   ×{weights['uniqueness']:.2f}",
        }
        for dim, label_str in dim_labels.items():
            earned = b.dim_scores.get(dim, 0.0)
            possible = weights.get(dim, 0.0)
            status = "✅" if earned >= possible * 0.8 else ("⚠️ " if earned > 0 else "❌")
            bar = _dim_bar(earned, possible)
            print(f"  {status}  {label_str}  {bar}  {earned:.3f}/{possible:.2f}")

        # Issues
        if b.issues:
            print()
            for issue in b.issues:
                print(f"  {issue}")

        # Suggestion
        if b.suggestion:
            print()
            print(f"  💡 STRONG VERSION:")
            print(f"     {b.suggestion[:110]}")

    print(f"\n{'=' * 80}")
    print()
    print("  HOW TO GET ALL BULLETS TO STRONG")
    print("  ─────────────────────────────────────────────────────────────────────────")
    print("  1. Add quantification to each project description:")
    print("     • User count / daily requests / data volume processed")
    print("     • Time saved (e.g., '3h → 5min') or efficiency gain (%)")
    print("     • Scale signals: number of APIs, pipelines, rooms, festivals, agents")
    print("  2. Start every bullet with an action verb (Built / Designed / Automated)")
    print("  3. Include the tech stack in the same sentence")
    print("  4. One clear achievement per bullet (split long descriptions)")
    print()
    print("  TARGET FORMAT:")
    print("  Built [what] with [tech] reducing/generating/serving [number][unit]")
    print()
    print(f"  SCORING WEIGHTS: impact×0.35  quant×0.25  keyword×0.20  leadership×0.10  uniqueness×0.10")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Score GitHub project bullets via Phase 8.1 pipeline")
    parser.add_argument("--username", default="andrew-nguyen-9", help="GitHub username")
    parser.add_argument(
        "--jd",
        default="",
        help="Optional job description text; extracts keywords for relevance scoring",
    )
    args = parser.parse_args()

    keywords = DEFAULT_KEYWORDS
    if args.jd:
        # Simple JD keyword extraction: words > 4 chars that aren't stopwords
        stopwords = {"with", "that", "this", "from", "have", "will", "your", "their"}
        jd_words = [w.strip(".,;:()") for w in args.jd.split() if len(w) > 4]
        jd_kws = [w for w in jd_words if w.lower() not in stopwords]
        keywords = list(set(DEFAULT_KEYWORDS + jd_kws))

    print(f"Fetching repos for @{args.username}…")
    repos = fetch_repos(args.username)
    print(f"Found {len(repos)} repos. Fetching READMEs…")

    readmes: dict[str, str] = {}
    for repo in repos:
        name = repo["name"]
        readme = fetch_readme(args.username, name)
        readmes[name] = readme
        status = f"({len(readme)} chars)" if readme else "(no README)"
        print(f"  {name}: {status}")

    print("\nScoring + rewriting bullets…")
    results = score_and_rewrite(repos, readmes, keywords)
    print_report(results)


if __name__ == "__main__":
    main()
