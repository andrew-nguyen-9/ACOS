# AI Career Operating System (ACOS)

## Technical Architecture

# Technology Stack

Frontend:

* Tauri
* React
* TypeScript
* TailwindCSS

Backend:

* Python
* FastAPI
* SQLAlchemy
* Pydantic

Database:

* SQLite

Vector Database:

* ChromaDB

Local AI:

* Ollama
* Qwen3 8B (default)

---

# High-Level Architecture

React/Tauri Frontend

↓

FastAPI Backend

↓

SQLite
+
ChromaDB
+
Ollama

↓

Knowledge Graph

---

# Repository Structure

backend/
frontend/
database/
docs/
scripts/
tests/

---

# Core Services

## Knowledge Graph Service

Responsible for:

* Entity storage
* Relationship mapping
* Evidence tracking

---

## Ingestion Service

Supports:

* TXT
* DOCX
* PDF
* Markdown
* GitHub
* Claude exports

Pipeline:

Import → Parse → Normalize → Embed → Store

---

## Resume Service

Pipeline:

Job Description
→ Keyword Extraction
→ Skill Extraction
→ Experience Matching
→ Resume Generation
→ ATS Analysis
→ DOCX Export

---

## Cover Letter Service

Pipeline:

Job Description
→ Voice Matching
→ Cover Letter Generation
→ Export

---

## ATS Service

Calculates:

* Keyword Match
* Skill Match
* Experience Match
* Industry Match

Produces ATS score.

---

## Question Service

Supports:

* Template questions
* Variable substitution
* Learning from edits

---

## Copilot Service

Workflow:

User Query
→ Retrieval
→ Evidence Ranking
→ Generation
→ Confidence Assignment

---

# Database Schema

Tables:

* experiences
* projects
* skills
* skill_evidence
* applications
* resumes
* cover_letters
* questions
* answers
* interview_outcomes
* generated_documents

---

# ChromaDB Collections

* experiences
* projects
* resumes
* cover_letters
* questions
* github
* claude_projects
* applications

---

# Learning Engine

Refresh after every 5 applications.

Tasks:

* Rebuild embeddings
* Update rankings
* Update ATS weighting
* Re-rank experiences
* Re-rank projects

---

# GitHub Integration

User:

andrew-nguyen-9

Analyze:

* README files
* Commits
* Languages
* Metadata

Generate:

* Skills
* Projects
* Resume bullets

---

# Claude Export Integration

Analyze:

* Prompt logic
* Agent workflows
* Architecture work
* Automation projects

Generate:

* Resume bullets
* Skills
* Interview stories

---

# Security Requirements

Validate:

* PDF ingestion
* DOCX ingestion
* File uploads
* Local storage

No plaintext secrets.

---

# Testing Requirements

Unit Tests:

90%+ coverage

Integration Tests:

Database
RAG
Generation

E2E:

Playwright

---

# Packaging

Deliver:

* DMG
* Installer
* Portable Build

Future:

* Windows
* Linux
