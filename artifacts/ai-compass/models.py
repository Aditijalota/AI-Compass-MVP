"""Small, plain data helpers for AI Compass assessments."""

from dataclasses import dataclass, asdict, field
from typing import Any


READINESS_CHECKS = {
    "owner": "A process owner and pilot participants are agreed",
    "process": "Process steps, exceptions, and success measures are understood",
    "data": "Required data and tools are available and approved for this scope",
    "review": "Human review, approvals, and a fallback are agreed",
}
READINESS_STATES = ["Not confirmed", "Needs work", "Confirmed"]
EFFORT_RANGES = {
    "baseline_hours": ("Baseline person-hours per week", None),
    "reduction_percent": ("Potential effort reduction on adopted work (%)", 100.0),
    "adoption_percent": ("Expected share of baseline work using the solution (%)", 100.0),
    "review_hours": ("Additional review and maintenance person-hours per week", None),
    "implementation_hours": ("One-time implementation person-hours", None),
}


@dataclass
class EffortAssumptions:
    """No inferred values: None means the user has not supplied an assumption."""

    baseline_hours: list[float | None] = field(default_factory=lambda: [None, None])
    reduction_percent: list[float | None] = field(default_factory=lambda: [None, None])
    adoption_percent: list[float | None] = field(default_factory=lambda: [None, None])
    review_hours: list[float | None] = field(default_factory=lambda: [None, None])
    implementation_hours: list[float | None] = field(default_factory=lambda: [None, None])
    scope: str = ""
    implementation_notes: str = ""
    readiness: dict[str, str] = field(default_factory=dict)
    confirmed: bool = False
    confirmed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    effort_assumptions: dict[str, Any] = field(default_factory=lambda: EffortAssumptions().to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

