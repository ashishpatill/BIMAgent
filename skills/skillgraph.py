from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class GraphErrorPolicy(enum.Enum):
    PROPAGATE = "propagate"
    SKIP = "skip"
    USE_DEFAULT = "use_default"


@dataclass
class SkillNode:
    name: str
    skill_ref: str
    dependencies: list[str] = field(default_factory=list)
    timeout: float = 30.0
    max_retries: int = 3
    error_policy: GraphErrorPolicy = GraphErrorPolicy.PROPAGATE
    input_mapping: dict[str, str] | None = None


class SkillGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, SkillNode] = {}

    def add_node(self, node: SkillNode) -> None:
        if node.name in self._nodes:
            raise ValueError(f"Node '{node.name}' already exists in graph")
        self._nodes[node.name] = node

    def get_node(self, name: str) -> SkillNode:
        if name not in self._nodes:
            raise KeyError(f"Node '{name}' not found in graph")
        return self._nodes[name]

    def remove_node(self, name: str) -> None:
        self._nodes.pop(name, None)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def node_names(self) -> list[str]:
        return list(self._nodes.keys())

    def topological_sort(self) -> list[str]:
        visited: set[str] = set()
        temp: set[str] = set()
        order: list[str] = []

        def dfs(node_name: str) -> None:
            if node_name in temp:
                raise ValueError(
                    f"Cycle detected in skill graph at node '{node_name}'"
                )
            if node_name in visited:
                return
            temp.add(node_name)
            node = self._nodes[node_name]
            for dep in node.dependencies:
                if dep not in self._nodes:
                    raise ValueError(
                        f"Missing dependency '{dep}' required by node '{node_name}'"
                    )
                dfs(dep)
            temp.remove(node_name)
            visited.add(node_name)
            order.append(node_name)

        for name in self._nodes:
            if name not in visited:
                dfs(name)

        return order

    def get_levels(self) -> list[list[str]]:
        order = self.topological_sort()
        levels: list[list[str]] = []
        processed: set[str] = set()

        remaining = list(order)
        while remaining:
            level: list[str] = []
            for name in list(remaining):
                node = self._nodes[name]
                if all(dep in processed for dep in node.dependencies):
                    level.append(name)
                    remaining.remove(name)
            if not level:
                raise ValueError(
                    "Cannot compute graph levels — possible cycle or missing dependency"
                )
            processed.update(level)
            levels.append(level)

        return levels

    def validate(self) -> list[str]:
        errors: list[str] = []
        for name, node in self._nodes.items():
            for dep in node.dependencies:
                if dep not in self._nodes:
                    errors.append(
                        f"Node '{name}' depends on missing node '{dep}'"
                    )
        try:
            self.topological_sort()
        except ValueError as e:
            errors.append(str(e))
        return errors
