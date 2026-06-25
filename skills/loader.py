from skills import SkillRegistry


def load_all_skills() -> list[dict]:
    """Load and return all registered skills."""
    return SkillRegistry.list_skills()
