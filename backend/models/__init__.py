# Import all models so SQLAlchemy registers them before create_all() is called.
from backend.models.base import Base, TimestampMixin, generate_uuid, utcnow
from backend.models.tenant import Tenant, TenantScopedMixin
from backend.models.auth import AuthCredential, AuthSession
from backend.models.audit import AuditLog
from backend.models.experience import Experience, ExperienceBullet
from backend.models.project import Project
from backend.models.skill import Skill, SkillEvidence, experience_skills_table, project_skills_table
from backend.models.application import Application, ApplicationTimeline
from backend.models.document import Document, IngestionLog
from backend.models.ingestion_failure import IngestionFailure
from backend.models.resume import Resume, ResumeTemplate, WritingProfile
from backend.models.question import Question, Answer
from backend.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge
from backend.models.outcome import OutcomeSignal
from backend.models.optimization import (
    OptimizationProposal, OptimizationLog, PromptVersion, ABExperiment, ABVariant,
)
from backend.models.generation import GenerationLog
from backend.models.metric import Metric
from backend.models.system_config import SystemConfig
from backend.models.memory import Memory
from backend.models.maintenance import MaintenanceSuggestion, MaintenanceAudit
from backend.models.signal import Signal
from backend.models.global_pattern import GlobalPattern

# Phase 12.7: the FTS5 lexical table is a virtual table (not a model), so
# create_all() can't build it. The app bootstraps schema via create_all (not
# alembic at runtime), so attach an after_create DDL hook on the shared metadata
# — fires on every create_all, idempotent (IF NOT EXISTS), same DDL the alembic
# migration uses for migration-managed databases.
from sqlalchemy import DDL, event as _event  # noqa: E402
from backend.services.rag.lexical import CREATE_FTS5_SQL  # noqa: E402

_event.listen(Base.metadata, "after_create", DDL(CREATE_FTS5_SQL))

__all__ = [
    "Base",
    "TimestampMixin",
    "generate_uuid",
    "utcnow",
    "Tenant",
    "TenantScopedMixin",
    "AuthCredential",
    "AuthSession",
    "AuditLog",
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
    "IngestionFailure",
    "Resume",
    "ResumeTemplate",
    "WritingProfile",
    "Question",
    "Answer",
    "KnowledgeGraphNode",
    "KnowledgeGraphEdge",
    "OutcomeSignal",
    "OptimizationProposal",
    "OptimizationLog",
    "PromptVersion",
    "ABExperiment",
    "ABVariant",
    "GenerationLog",
    "Metric",
    "SystemConfig",
    "Memory",
    "MaintenanceSuggestion",
    "MaintenanceAudit",
    "Signal",
    "GlobalPattern",
]
