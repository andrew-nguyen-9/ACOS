# Import all models so SQLAlchemy registers them before create_all() is called.
from backend.models.base import Base, TimestampMixin, generate_uuid, utcnow
from backend.models.experience import Experience, ExperienceBullet
from backend.models.project import Project
from backend.models.skill import Skill, SkillEvidence, experience_skills_table, project_skills_table
from backend.models.application import Application, ApplicationTimeline
from backend.models.document import Document, IngestionLog
from backend.models.resume import Resume, ResumeTemplate, WritingProfile
from backend.models.question import Question, Answer
from backend.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge
from backend.models.outcome import OutcomeSignal
from backend.models.optimization import OptimizationProposal
from backend.models.generation import GenerationLog
from backend.models.system_config import SystemConfig

__all__ = [
    "Base",
    "TimestampMixin",
    "generate_uuid",
    "utcnow",
    "Experience",
    "ExperienceBullet",
    "Project",
    "Skill",
    "SkillEvidence",
    "experience_skills_table",
    "project_skills_table",
    "Application",
    "ApplicationTimeline",
    "Document",
    "IngestionLog",
    "Resume",
    "ResumeTemplate",
    "WritingProfile",
    "Question",
    "Answer",
    "KnowledgeGraphNode",
    "KnowledgeGraphEdge",
    "OutcomeSignal",
    "OptimizationProposal",
    "GenerationLog",
    "SystemConfig",
]
