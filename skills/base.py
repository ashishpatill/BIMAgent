from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SkillInput:
    query: str
    context: dict | None = None


@dataclass
class SkillOutput:
    result: dict
    error: str | None = None


class BaseSkill(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    async def execute(self, input: SkillInput) -> SkillOutput: ...
