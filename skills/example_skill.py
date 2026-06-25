from skills.base import BaseSkill, SkillInput, SkillOutput


class ExampleSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "example_skill"

    @property
    def description(self) -> str:
        return "An example placeholder skill for demonstration"

    async def execute(self, input: SkillInput) -> SkillOutput:
        return SkillOutput(
            result={"message": f"Example skill executed with query: {input.query}"}
        )
