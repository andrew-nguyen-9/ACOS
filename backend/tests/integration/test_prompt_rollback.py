"""End-to-end: PromptLoader resolves active/pinned/rolled-back registry versions,
falling back to on-disk yaml for prompts never deployed (Phase 11.2)."""
from backend.services.prompt_loader import PromptLoader
from backend.services.prompts.registry import PromptRegistry


def test_loader_resolves_active_then_rolled_back(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("greet", "system: ONE\nuser_template: a")
    reg.deploy("greet", "system: TWO\nuser_template: b")
    loader = PromptLoader(test_session)
    assert loader.load("greet")["system"] == "TWO"

    reg.rollback("greet", "v1")
    assert loader.load("greet")["system"] == "ONE"
    assert loader.load("greet")["version"] == "v1"


def test_loader_pins_explicit_version(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("greet", "system: ONE")
    reg.deploy("greet", "system: TWO")
    loader = PromptLoader(test_session)
    assert loader.load("greet", version="v1")["system"] == "ONE"


def test_loader_falls_back_to_disk_when_not_in_registry(test_session):
    # extract_entities ships on disk and was never deployed to the registry.
    loader = PromptLoader(test_session)
    result = loader.load("extract_entities")
    assert "system" in result
    assert result["version"]


def test_loader_no_session_uses_disk(test_session):
    # Backward compatibility: existing callers use PromptLoader() with no session.
    result = PromptLoader().load("extract_entities")
    assert "system" in result
