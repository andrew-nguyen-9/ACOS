/**
 * Phase 17.2 — heuristic job-posting extraction (pure, DOM-free so it's unit
 * testable). Works on an HTML string: strip tags to text, pull the title from
 * <title>/<h1>, and slice responsibilities/qualifications by section heading.
 *
 * Heuristic-first (Q8): the local-LLM fallback (via the backend) is only invoked
 * when this yields low confidence — never per capture.
 */

const _TAG = /<[^>]+>/g;
const _WS = /[ \t ]+/g;

function stripTags(html) {
  // Drop script/style bodies entirely before stripping the rest.
  const noScript = html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ");
  return noScript.replace(_TAG, "\n").replace(_WS, " ");
}

function firstMatch(html, re) {
  const m = html.match(re);
  return m ? stripTags(m[1]).trim() : "";
}

/** Slice the text block that follows a heading matching `labels` until the next heading. */
function sectionAfter(text, labels) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const isHeading = (l) => l.length < 60 && /[a-z]/i.test(l);
  for (let i = 0; i < lines.length; i++) {
    const low = lines[i].toLowerCase();
    if (labels.some((lbl) => low.startsWith(lbl) || low === lbl)) {
      const out = [];
      for (let j = i + 1; j < lines.length; j++) {
        const lowj = lines[j].toLowerCase();
        if (SECTION_LABELS.some((lbl) => lowj.startsWith(lbl)) && isHeading(lines[j])) break;
        out.push(lines[j]);
      }
      return out.join("\n").trim();
    }
  }
  return "";
}

const SECTION_LABELS = [
  "responsibilities", "what you'll do", "what you will do", "the role", "about the role",
  "qualifications", "requirements", "what you'll need", "what we're looking for",
  "about us", "benefits", "perks",
];

export function extractFromHtml(html) {
  const title =
    firstMatch(html, /<h1[^>]*>([\s\S]*?)<\/h1>/i) ||
    firstMatch(html, /<title[^>]*>([\s\S]*?)<\/title>/i);
  const company =
    firstMatch(html, /<meta[^>]+property=["']og:site_name["'][^>]+content=["']([^"']+)["']/i) ||
    firstMatch(html, /<meta[^>]+name=["']author["'][^>]+content=["']([^"']+)["']/i);
  const text = stripTags(html);
  const responsibilities = sectionAfter(text, [
    "responsibilities", "what you'll do", "what you will do", "the role", "about the role",
  ]);
  const qualifications = sectionAfter(text, [
    "qualifications", "requirements", "what you'll need", "what we're looking for",
  ]);

  // Confidence: high if we found a title AND at least one section.
  const found = [title, responsibilities, qualifications].filter(Boolean).length;
  const confidence = title && (responsibilities || qualifications) ? "high" : found ? "low" : "none";

  return {
    title,
    company,
    responsibilities,
    qualifications,
    raw_text: text.slice(0, 20000),
    confidence,
  };
}
