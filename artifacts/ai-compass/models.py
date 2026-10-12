"""Small, plain data helpers for AI Compass assessments."""

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class Assessment:
    id: int | None
    created_at: str
    title: str
    department: str
    role: str
    problem_scale: str
    rollout_scale: str
    solution_pattern: str
    explanation: str
    alternatives: list[str]
    benefits: list[str]
    missing_information: list[str]
    readiness_concerns: list[str]
    next_steps: list[str]
    discovery: dict[str, Any]
    is_example: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

