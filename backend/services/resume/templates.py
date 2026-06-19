from __future__ import annotations

TEMPLATE_NAMES = ["software", "ai", "product", "consulting", "data_analytics", "healthcare"]

RESUME_TEMPLATES: dict[str, dict] = {
    "software": {
        "layout": "single_column",
        "bullet_style": "action_impact",
        "sections": ["summary", "experience", "skills", "projects", "education"],
        "skills_position": "after_experience",
        "max_experience_bullets": 4,
        "emphasis": "technical_depth",
    },
    "ai": {
        "layout": "single_column",
        "bullet_style": "action_impact",
        "sections": ["summary", "experience", "projects", "skills", "education"],
        "skills_position": "after_projects",
        "max_experience_bullets": 3,
        "emphasis": "research_and_systems",
    },
    "product": {
        "layout": "single_column",
        "bullet_style": "metrics_first",
        "sections": ["summary", "experience", "skills", "education"],
        "skills_position": "end",
        "max_experience_bullets": 4,
        "emphasis": "stakeholder_impact",
    },
    "consulting": {
        "layout": "single_column",
        "bullet_style": "star",
        "sections": ["summary", "experience", "education", "skills"],
        "skills_position": "end",
        "max_experience_bullets": 4,
        "emphasis": "client_outcomes",
    },
    "data_analytics": {
        "layout": "single_column",
        "bullet_style": "action_impact",
        "sections": ["summary", "experience", "skills", "projects", "education"],
        "skills_position": "after_experience",
        "max_experience_bullets": 4,
        "emphasis": "data_tools_and_business_impact",
    },
    "healthcare": {
        "layout": "single_column",
        "bullet_style": "action_impact",
        "sections": ["summary", "experience", "education", "certifications", "skills"],
        "skills_position": "end",
        "max_experience_bullets": 4,
        "emphasis": "clinical_and_compliance",
    },
}


def get_template(name: str) -> dict:
    if name not in RESUME_TEMPLATES:
        raise ValueError(f"Unknown template: '{name}'. Valid: {TEMPLATE_NAMES}")
    return RESUME_TEMPLATES[name]
