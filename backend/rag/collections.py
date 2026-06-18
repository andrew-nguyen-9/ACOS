from enum import Enum


class CollectionName(str, Enum):
    EXPERIENCES = "acos_experiences"
    PROJECTS = "acos_projects"
    SKILLS = "acos_skills"
    RESUMES = "acos_resumes"
    COVER_LETTERS = "acos_cover_letters"
    QUESTIONS = "acos_questions"
    ANSWERS = "acos_answers"
    JOB_DESCRIPTIONS = "acos_job_descriptions"
    GITHUB = "acos_github"
    CLAUDE_EXPORTS = "acos_claude_exports"


# Metadata config per collection (hnsw:space = cosine similarity)
COLLECTION_CONFIGS: dict[str, dict] = {
    CollectionName.EXPERIENCES: {"hnsw:space": "cosine"},
    CollectionName.PROJECTS: {"hnsw:space": "cosine"},
    CollectionName.SKILLS: {"hnsw:space": "cosine"},
    CollectionName.RESUMES: {"hnsw:space": "cosine"},
    CollectionName.COVER_LETTERS: {"hnsw:space": "cosine"},
    CollectionName.QUESTIONS: {"hnsw:space": "cosine"},
    CollectionName.ANSWERS: {"hnsw:space": "cosine"},
    CollectionName.JOB_DESCRIPTIONS: {"hnsw:space": "cosine"},
    CollectionName.GITHUB: {"hnsw:space": "cosine"},
    CollectionName.CLAUDE_EXPORTS: {"hnsw:space": "cosine"},
}

ALL_COLLECTION_NAMES: list[str] = [c.value for c in CollectionName]
