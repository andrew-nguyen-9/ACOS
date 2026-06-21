from __future__ import annotations

import re

# ── Comprehensive action verb set ────────────────────────────────────────────
# Synthesized from: Harvard FAS, WIT Coop & Careers, Yale OCS, Notre Dame MBA,
# Smith School MBA Resume Guidelines, and the Phase 8.1 Resume Engine Spec.
#
# Rule: bullets MUST begin with one of these verbs (past tense for prior roles,
# present tense for current role). All stored in lowercase for case-insensitive
# comparison at enforcement time.

ACTION_VERBS: frozenset[str] = frozenset({
    # ── Achievement / Results ────────────────────────────────────────────────
    "accomplished", "achieved", "attained", "exceeded", "earned", "finished",
    "outperformed", "overcame", "reached", "showcased", "succeeded", "surpassed",
    "targeted", "won", "completed", "proved",
    # ── Leadership / Management ──────────────────────────────────────────────
    "administered", "assigned", "authorized", "awarded", "certified", "chaired",
    "championed", "changed", "consolidated", "contracted", "controlled",
    "coordinated", "cultivated", "decided", "delegated", "directed", "dispatched",
    "drove", "enabled", "enforced", "established", "executed", "expanded",
    "finalized", "fostered", "founded", "generated", "handled", "headed",
    "hired", "hosted", "impacted", "increased", "initiated", "instituted",
    "launched", "led", "managed", "mastered", "mentored", "mobilized",
    "motivated", "navigated", "orchestrated", "organized", "originated",
    "oversaw", "pioneered", "planned", "predicted", "presided", "prioritized",
    "produced", "qualified", "recommended", "recruited", "regulated",
    "reorganized", "reviewed", "scheduled", "secured", "selected", "shaped",
    "spearheaded", "stimulated", "strengthened", "supervised", "surpassed",
    "supervised", "terminated", "trained", "unified",
    # ── Communication / Collaboration ───────────────────────────────────────
    "addressed", "amplified", "arbitrated", "arranged", "authored", "bridged",
    "briefed", "campaigned", "collaborated", "communicated", "composed",
    "convinced", "corresponded", "delivered", "documented", "drafted", "edited",
    "energized", "enlisted", "explained", "formulated", "influenced",
    "informed", "integrated", "interpreted", "lectured", "liaised", "mediated",
    "moderated", "negotiated", "partnered", "persuaded", "presented", "promoted",
    "publicized", "reconciled", "recruited", "reported", "rewrote", "solicited",
    "spoke", "suggested", "summarized", "synthesized", "translated", "verbalized",
    "wrote",
    # ── Research / Analysis ─────────────────────────────────────────────────
    "analyzed", "appraised", "assessed", "audited", "calculated", "cited",
    "clarified", "classified", "collected", "compiled", "computed", "concluded",
    "conducted", "critiqued", "derived", "detected", "determined", "diagnosed",
    "discovered", "dissected", "evaluated", "examined", "experimented",
    "explored", "extracted", "forecasted", "formed", "gathered", "identified",
    "inspected", "interpreted", "interviewed", "investigated", "located",
    "mapped", "measured", "modeled", "monitored", "projected", "quantified",
    "researched", "resolved", "reviewed", "scrutinized", "studied", "surveyed",
    "systematized", "tested", "validated", "verified",
    # ── Technical / Engineering ──────────────────────────────────────────────
    "architected", "assembled", "automated", "built", "coded", "computed",
    "constructed", "converted", "deployed", "designed", "developed", "devised",
    "digitized", "engineered", "fabricated", "implemented", "installed",
    "integrated", "maintained", "modernized", "operated", "optimized",
    "overhauled", "programmed", "redesigned", "reduced", "remodeled",
    "repaired", "restored", "scaled", "serviced", "simplified", "solved",
    "standardized", "streamlined", "upgraded",
    # ── Teaching / Coaching ──────────────────────────────────────────────────
    "adapted", "advised", "coached", "counseled", "demystified", "educated",
    "enabled", "encouraged", "facilitated", "guided", "individualized",
    "informed", "inspired", "instilled", "instructed", "mentored", "motivated",
    "persuaded", "stimulated", "taught", "trained", "tutored",
    # ── Quantitative / Financial ─────────────────────────────────────────────
    "accelerated", "acquired", "allocated", "balanced", "boosted", "budgeted",
    "capitalized", "centralized", "closed", "conserved", "decreased", "deducted",
    "delivered", "enhanced", "expedited", "expanded", "forecasted", "gained",
    "generated", "increased", "launched", "maintained", "marketed", "maximized",
    "merged", "minimized", "outpaced", "projected", "purchased", "reconciled",
    "reduced", "restructured", "saved", "secured", "sold", "sourced",
    "sustained", "transformed", "upsold", "yielded",
    # ── Creative / Strategic ─────────────────────────────────────────────────
    "conceived", "conceptualized", "created", "customized", "illustrated",
    "improved", "invented", "modified", "originated", "performed", "published",
    "redesigned", "revised", "revitalized", "shaped", "visualized",
    # ── Helping / Support ────────────────────────────────────────────────────
    "accompanied", "aided", "amended", "applied", "attended", "contributed",
    "cooperated", "demonstrated", "expedited", "familiarized", "furthered",
    "participated", "prevented", "proposed", "provided", "referred",
    "rehabilitated", "represented", "served", "supported", "volunteered",
    # ── Organizational ───────────────────────────────────────────────────────
    "approved", "cataloged", "changed", "compiled", "completed", "controlled",
    "defined", "distributed", "executed", "expanded", "filed", "formalized",
    "gathered", "implemented", "inspected", "launched", "maintained",
    "monitored", "prepared", "processed", "produced", "purchased", "recorded",
    "registered", "reinforced", "reorganized", "responded", "retrieved",
    "screened", "settled", "simplified", "sourced", "specified", "steered",
    "structured", "submitted", "tabulated", "unified", "updated",
    # ── Forensic / Compliance (Secretariat domain) ───────────────────────────
    "attended", "collaborated", "conducted", "contributed", "coordinated",
    "executed", "extracted", "identified", "investigated", "modeled",
    "performed", "processed", "reconciled", "standardized", "uncovered",
    # ── Filler-replacement targets (leveraged→used, helped→supported) ────────
    "used",
    # ── Additional high-frequency resume verbs ───────────────────────────────
    "accomplished", "achieved", "acted", "addressed", "aligned", "allocated",
    "analyzed", "anticipated", "appointed", "assessed", "assisted", "assured",
    "broadened", "certified", "championed", "clarified", "classified",
    "collected", "compiled", "computed", "coordinated", "created",
    "critiqued", "cultivated", "decided", "decreased", "delegated",
    "designated", "determined", "developed", "digitized", "directed",
    "discovered", "dispatched", "documented", "drafted", "drove",
    "earned", "educated", "enabled", "encouraged", "enforced", "enlisted",
    "established", "evaluated", "examined", "exceeded", "executed",
    "expanded", "expedited", "explained", "extracted", "facilitated",
    "finalized", "focused", "formulated", "fostered", "founded",
    "gained", "generated", "guided", "handled", "headed", "hired",
    "identified", "implemented", "improved", "increased", "influenced",
    "initiated", "inspected", "installed", "integrated", "introduced",
    "invented", "investigated", "launched", "led", "maintained",
    "managed", "marketed", "maximized", "minimized", "mobilized",
    "monitored", "motivated", "navigated", "negotiated", "operated",
    "optimized", "orchestrated", "organized", "originated", "oversaw",
    "partnered", "performed", "planned", "prepared", "presented",
    "prioritized", "produced", "programmed", "proposed", "provided",
    "published", "qualified", "recommended", "recruited", "reduced",
    "regulated", "reorganized", "reported", "represented", "researched",
    "resolved", "reviewed", "revised", "revitalized", "scheduled",
    "secured", "selected", "simplified", "sold", "solved", "specified",
    "standardized", "streamlined", "strengthened", "structured",
    "summarized", "supervised", "surveyed", "synthesized", "systematized",
    "targeted", "taught", "tested", "trained", "transformed", "translated",
    "unified", "updated", "upgraded", "validated", "verified",
    "visualized", "volunteered", "won", "wrote",
})

# Leading words that are NOT action verbs but may precede one.
# Stripped so the real verb is preserved rather than prepending "Led".
_LEADING_ADVERBS: frozenset[str] = frozenset({
    "independently", "directly", "proactively", "strategically", "simultaneously",
    # Discourse connectors
    "also", "additionally", "subsequently",
})

# ── Filler replacement map ───────────────────────────────────────────────────
# Ordered longest-first so longer patterns match before their substrings.
# Sources: WIT Grammar Guide, Harvard Quick Tips, Smith MBA guidelines.
_FILLER_REPLACEMENTS: list[tuple[str, str]] = [
    # ── Passive openers / responsibility language ────────────────────────────
    (r"(?i)was\s+responsible\s+for\s*", ""),
    (r"(?i)responsible\s+for\s*", ""),
    (r"(?i)was\s+tasked\s+with\s*", ""),
    (r"(?i)tasked\s+with\s*", ""),
    (r"(?i)was\s+able\s+to\s*", ""),
    (r"(?i)in\s+order\s+to\b", "to"),
    # ── Non-descript verb replacements (WIT guide) ───────────────────────────
    (r"(?i)worked\s+with\b", "partnered with"),
    (r"(?i)worked\s+on\b", "developed"),
    (r"(?i)\bhelped\s+to\b", ""),
    (r"(?i)\bhelped\b", "Supported"),
    (r"(?i)\butilized\b", "Used"),
    (r"(?i)\bleveraged\b", "Used"),
    # ── Weak/redundant adverbs (WIT guide: "favor strong verbs over adverbs") ─
    (r"(?i)\bsuccessfully\b", ""),
    (r"(?i)\beffectively\b", ""),
    (r"(?i)\befficiently\b", ""),
    (r"(?i)\bconsistently\b", ""),
    (r"(?i)\bcontinually\b", ""),
    (r"(?i)\bskillfully\b", ""),
    (r"(?i)\bseamlessly\b", ""),
    (r"(?i)\bproactively\b", ""),
    # ── Filler qualifiers ────────────────────────────────────────────────────
    (r"(?i)multiple\s+different\b", "multiple"),
    (r"(?i)a\s+number\s+of\b", ""),
    (r"(?i)\bvarious\b", ""),
    # ── Experience-with patterns (WIT: non-descript) ─────────────────────────
    (r"(?i)experience\s+(?:with|in)\b\s*", ""),
    # ── Article at sentence start (Smith MBA: "limit use of articles") ───────
    (r"(?i)^(?:the|a|an)\s+", ""),
]

# Pre-compiled for performance
_COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pat), repl) for pat, repl in _FILLER_REPLACEMENTS
]

_MULTI_SPACE = re.compile(r" {2,}")


class BulletRewriter:
    """Clean, normalize, and compact resume bullet text.

    Non-destructive: always returns new strings, never modifies originals.

    Encoding rules from: Harvard FAS, WIT Coop & Careers, Yale OCS,
    Notre Dame MBA, and Smith School MBA Resume Guidelines.
    """

    def normalize(self, text: str) -> str:
        """Apply filler-phrase replacement rules and collapse whitespace."""
        for pattern, replacement in _COMPILED:
            text = pattern.sub(replacement, text)
        return _MULTI_SPACE.sub(" ", text).strip()

    def enforce_action_verb(self, text: str) -> str:
        """Ensure the bullet begins with an allowed action verb.

        Strategy (in order):
        1. If first word is already a valid verb → no change.
        2. If first word is a leading adverb and second word is a verb →
           strip the adverb (avoids "Led Independently built...").
        3. Otherwise → prepend "Led ".
        """
        words = text.split()
        if not words:
            return text
        first = words[0].lower().rstrip(".,;:")
        if first in ACTION_VERBS:
            return text
        # Strip leading adverb when the verb immediately follows
        if first in _LEADING_ADVERBS and len(words) > 1:
            second = words[1].lower().rstrip(".,;:")
            if second in ACTION_VERBS:
                return " ".join([words[1].capitalize()] + words[2:])
        return f"Led {text}"

    def compress(self, text: str) -> str:
        """Normalize then enforce action verb. Core pipeline step."""
        return self.enforce_action_verb(self.normalize(text))

    def force_single_line(self, text: str, max_chars: int = 88) -> str:
        """Compress then truncate with '...' if still over max_chars."""
        compressed = self.compress(text)
        if len(compressed) <= max_chars:
            return compressed
        return compressed[: max_chars - 3] + "..."
