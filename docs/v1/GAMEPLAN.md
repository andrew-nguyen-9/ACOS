# AI Career Operating System (ACOS)

# Technical Architecture Specification v1.0

## Guiding Principle

Claude should think like a Principal Software Engineer building a long-lived production product, not a prototype.

Prioritize:

1. Maintainability
2. Extensibility
3. Traceability
4. Testability
5. Reliability
6. Performance

over implementation speed.

---

# System Overview

AI Career Operating System (ACOS) is a local-first desktop application that helps users:

* Generate resumes
* Generate cover letters
* Generate application answers
* Track applications
* Improve interview rates
* Search career history
* Act as a personal career copilot

The application should continuously learn from:

* User experiences
* Application outcomes
* GitHub repositories
* Historical resumes
* Historical cover letters
* Claude project exports
* Question banks

without requiring external AI APIs.

---

# High-Level Architecture

```text
┌──────────────────────────┐
│      React Frontend      │
│       (Tauri UI)         │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│      FastAPI Backend     │
└────────────┬─────────────┘
             │
 ┌───────────┼───────────┐
 ▼           ▼           ▼

SQLite    ChromaDB    Ollama
Database  Vectors     Local LLM

             │
             ▼

     Knowledge Graph
```

---

# Repository Structure

```text
AI-Career-OS/

apps/
├── desktop/

backend/
├── api/
├── services/
├── models/
├── repositories/
├── ingestion/
├── prompts/
├── ranking/
├── rag/
├── ats/
├── analytics/
├── jobs/
├── tests/

frontend/
├── src/
│   ├── pages/
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── stores/
│   ├── layouts/

database/
├── migrations/
├── seed/

docs/

examples/

scripts/
```

---

# Core Modules

## 1. Knowledge Graph Engine

Purpose:

Single source of truth.

Stores relationships between:

* Experiences
* Skills
* Projects
* Companies
* Applications
* Resumes
* Cover Letters
* Questions
* Answers
* Outcomes

---

## 2. Document Ingestion Engine

Supported:

```text
TXT
DOCX
PDF
Markdown
GitHub
Claude Exports
```

Pipeline:

```text
Import
→ Parse
→ Normalize
→ Extract Entities
→ Store Metadata
→ Generate Embeddings
→ Create Knowledge Graph Links
```

---

# Database Schema

## experiences

```sql
id
title
company
description
start_date
end_date
source
created_at
updated_at
```

---

## projects

```sql
id
name
description
industry
repository_url
confidence_level
created_at
```

---

## skills

```sql
id
name
category
proficiency
confidence_level
```

---

## skill_evidence

```sql
id
skill_id
source_id
evidence_text
confidence_level
```

---

## applications

```sql
id
company
position
industry
job_description
status
date_applied
salary
outcome
```

---

## resumes

```sql
id
application_id
template_used
ats_score
file_path
```

---

## cover_letters

```sql
id
application_id
word_count
file_path
```

---

## questions

```sql
id
question_template
industry
category
```

---

## answers

```sql
id
question_id
answer
edited_answer
```

---

## interview_outcomes

```sql
id
application_id
outcome
date_recorded
```

---

## generated_documents

```sql
id
type
version
source_application
file_path
```

---

# ChromaDB Collections

Create collections:

```text
experiences
projects
skills
resumes
cover_letters
questions
answers
github
claude_projects
applications
job_descriptions
```

---

# Knowledge Graph Relationships

```text
Experience
    ├── Skills
    ├── Projects
    ├── Companies
    └── Outcomes

Project
    ├── Skills
    ├── Technologies
    └── Evidence

Application
    ├── Resume
    ├── Cover Letter
    ├── Questions
    └── Outcome
```

---

# Resume Engine

## Workflow

Input:

```text
Company
Position
Job Description
```

Pipeline:

```text
Industry Detection
↓
Keyword Extraction
↓
Skill Extraction
↓
Experience Matching
↓
Project Matching
↓
Resume Template Recommendation
↓
Resume Generation
↓
ATS Analysis
↓
DOCX Export
```

---

# Resume Generation Rules

Must:

* Be exactly one page
* Include skills section
* Include measurable outcomes where verified
* Include projects when relevant
* Preserve ATS compatibility

Must not:

* Invent metrics
* Invent dates
* Invent certifications

---

# ATS Scoring Engine

## Score Components

```text
Keyword Match       35%
Skill Match         25%
Experience Match    20%
Industry Match      10%
Education Match     10%
```

---

## ATS Output

```json
{
  "score": 88,
  "missing_keywords": [],
  "recommended_additions": [],
  "industry_alignment": 92
}
```

---

# Cover Letter Engine

Input:

```text
Company
Position
Job Description
Desired Length
```

Lengths:

```text
100
250
400
1 Page
Custom
```

Output:

```text
DOCX
TXT
```

---

# Cover Letter Learning

Analyze:

Historical cover letters

Extract:

```text
Tone
Voice
Structure
Personalization Style
```

Store as:

```text
Writing Profile
```

---

# Question & Answer Engine

Generate:

```text
Short
Medium
Long
```

Question variables:

```text
{{company}}
{{position}}
{{industry}}
{{product}}
{{tech_stack}}
```

---

# Answer Learning Pipeline

Store:

```text
Original Answer
Edited Answer
Diff
```

Use edits to:

* Improve retrieval
* Improve ranking
* Improve future answers

---

# Career Copilot

Purpose:

RAG-powered assistant.

Searches:

```text
Experiences
Projects
GitHub
Applications
Resumes
Cover Letters
Question Bank
Claude Projects
```

before generating responses.

---

# Copilot Agent Workflow

```text
User Question
↓
Intent Detection
↓
Retrieval
↓
Evidence Ranking
↓
Response Generation
↓
Confidence Assignment
```

---

# Confidence Engine

Every generated statement receives:

```text
Verified
Strong Inference
Weak Inference
```

---

## Confidence Rules

Verified:

Direct evidence exists.

Strong Inference:

Multiple supporting records.

Weak Inference:

Model-generated assumption.

Requires user confirmation.

---

# GitHub Ingestion Pipeline

Repository Analysis:

```text
README
Languages
Commits
Structure
Metadata
```

Generate:

```text
Projects
Skills
Resume Bullets
Interview Examples
```

---

# Claude Export Ingestion Pipeline

Analyze:

```text
Project Files
Prompt Logic
Agent Workflows
Architecture Discussions
Automation Projects
```

Generate:

```text
Skills
Projects
Achievements
Interview Stories
```

---

# Learning Engine

Refresh every 5 applications.

Process:

```text
Re-index documents
Rebuild embeddings
Update ATS rankings
Update project rankings
Update experience rankings
Update outcome model
```

---

# Ranking Engine

Positive Signals:

```text
Interview
Recruiter Contact
Final Round
Offer
```

Negative Signals:

```text
No Response
Rejection
```

Weights:

```text
No Response = 0

Interview = 5

Recruiter Contact = 7

Final Round = 15

Offer = 25
```

---

# Outcome Optimization Engine

Track:

```text
Resume Template
ATS Score
Industry
Question Answers
Projects Used
```

Determine:

```text
Highest Interview Conversion
```

---

# Prompt Library Structure

```text
prompts/

resume/
cover_letter/
ats/
copilot/
questions/
ranking/
retrieval/
```

Every prompt:

```yaml
name:
version:
purpose:
input_schema:
output_schema:
```

---

# API Design

## Resume Generation

POST

```text
/api/resume/generate
```

Request:

```json
{
  "company": "",
  "position": "",
  "job_description": ""
}
```

---

## Cover Letter

POST

```text
/api/cover-letter/generate
```

---

## ATS Analysis

POST

```text
/api/ats/analyze
```

---

## Copilot Chat

POST

```text
/api/copilot/chat
```

---

## Application Tracking

CRUD:

```text
/api/applications
```

---

# Frontend Pages

## Dashboard

Metrics:

```text
Applications
Interview Rate
Recent Documents
ATS Trends
```

---

## Resume Builder

Features:

```text
Generate
Preview
Edit
Export
```

---

## Cover Letter Builder

Features:

```text
Generate
Edit
Export
```

---

## Question Bank

Features:

```text
Import
Generate
Edit
Categorize
```

---

## Career Copilot

Chat interface.

Evidence panel.

Confidence panel.

Sources panel.

---

## Application CRM

Pipeline view:

```text
Draft
Applied
Interview
Offer
Rejected
```

---

# Testing Strategy

## Unit Tests

Coverage:

```text
>90%
```

---

## Integration Tests

Cover:

```text
Database
RAG
Generation
Tracking
```

---

## End-to-End Tests

Playwright required.

Test:

```text
Resume Generation
Cover Letter Generation
Application Creation
Copilot Usage
```

---

# Logging

Structured logs:

```text
generation_logs
retrieval_logs
ats_logs
application_logs
```

---

# Observability

Track:

```text
Generation Time
Retrieval Quality
ATS Accuracy
Interview Conversion
```

---

# Security

Review:

```text
File Parsing
PDF Parsing
DOCX Parsing
Local Storage
Exports
GitHub Sync
```

No secrets should be stored in plaintext.

---

# Packaging

Target:

macOS

Deliver:

```text
DMG
Installer
Portable Build
```

Future:

```text
Windows
Linux
```

---

# Plugin Orchestration Requirements

Claude must use the plugin orchestration strategy defined in:

```text
07_PLUGIN_ORCHESTRATION.md
```

Feature completion requires:

```text
Feature Design
Code Review
Security Review
Type Checking
Playwright Testing
Documentation
Commit Generation
```

---

# Definition of Done

The application is complete when:

* Runs fully offline
* Generates resumes
* Generates cover letters
* Generates application answers
* Tracks applications
* Learns from outcomes
* Maintains evidence traceability
* Provides ATS analysis
* Provides Career Copilot
* Supports GitHub ingestion
* Supports Claude export ingestion
* Requires no external AI APIs
* Operates entirely with local models

This is a production application, not a prototype.