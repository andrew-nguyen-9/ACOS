# ADR-001: Local-First Architecture

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Andrew Nguyen

---

## Context

ACOS handles sensitive career data: resumes, job applications, employer details, salary
ranges, recruiter contacts, and personally identifiable information. The system must
generate content using AI capabilities.

Cloud-hosted AI APIs (OpenAI, Anthropic) would require transmitting this data to third-party
servers. The user has deep expertise in digital privacy and regulatory compliance and has
explicitly ruled out this approach.

---

## Decision

All processing — LLM inference, embeddings, vector search, structured storage, and file
parsing — runs locally on the user's machine. No data is transmitted to external services
during normal operation.

---

## Consequences

**Positive:**
- Complete data privacy; career data never leaves the machine
- No API costs; unlimited usage
- Works fully offline after initial setup
- No rate limits or service outages from third-party providers
- Aligns with user's digital privacy expertise and values

**Negative:**
- LLM quality ceiling is lower than frontier models (Qwen3 8B vs GPT-4o)
- Requires non-trivial local compute (8GB+ RAM, ideally GPU)
- Setup complexity higher than a cloud-connected app
- Model updates require manual re-download

**Mitigations:**
- Qwen3 8B has sufficient quality for structured generation tasks (resume, cover letter)
- The knowledge graph grounds generation in real evidence, compensating for model limits
- First-run setup wizard guides the user through Ollama installation

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| OpenAI API | Transmits private career data to third party |
| Anthropic API | Same privacy concern; also contradicts "no external AI APIs" requirement |
| Hybrid (local default, cloud opt-in) | Adds complexity; not needed for stated use case |
| Open-source cloud (self-hosted) | Violates "local" requirement; adds deployment complexity |
