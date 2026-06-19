import pytest
from backend.services.resume.templates import get_template, RESUME_TEMPLATES, TEMPLATE_NAMES


def test_all_six_templates_defined():
    assert set(TEMPLATE_NAMES) == {"software", "ai", "product", "consulting", "data_analytics", "healthcare"}


def test_get_template_returns_dict():
    for name in TEMPLATE_NAMES:
        tmpl = get_template(name)
        assert "sections" in tmpl
        assert "layout" in tmpl


def test_get_template_unknown_raises():
    with pytest.raises(ValueError, match="Unknown template"):
        get_template("nonexistent")


def test_software_template_has_skills_section():
    tmpl = get_template("software")
    assert "skills" in tmpl["sections"]


def test_consulting_template_bullet_style():
    tmpl = get_template("consulting")
    assert tmpl["bullet_style"] == "star"
