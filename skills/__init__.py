from skills.base import BaseSkill, SkillInput, SkillOutput


class SkillRegistry:
    """Global registry for agent skills"""
    _skills: dict[str, BaseSkill] = {}

    @classmethod
    def register(cls, skill: BaseSkill):
        cls._skills[skill.name] = skill

    @classmethod
    def get(cls, name: str) -> BaseSkill:
        if name not in cls._skills:
            raise KeyError(f"Skill '{name}' not registered")
        return cls._skills[name]

    @classmethod
    def list_skills(cls) -> list[dict]:
        return [{"name": s.name, "description": s.description} for s in cls._skills.values()]


from skills.example_skill import ExampleSkill
from skills.search_bimindex import BIMIndexSearchSkill
from skills.extract_bimextract import BIMExtractSkill

SkillRegistry.register(ExampleSkill())
SkillRegistry.register(BIMIndexSearchSkill())
SkillRegistry.register(BIMExtractSkill())

__all__ = ["SkillRegistry", "BaseSkill", "SkillInput", "SkillOutput"]
