"""Small export helpers used by the assessment detail screen."""

import json
from classification import estimate_opportunity, evaluate_pilot


def hours_range(values) -> str:
    if values is None:
        return "Not estimated — inputs missing or unconfirmed"
    return f"{values[0]:.2f} to {values[1]:.2f} person-hours"


def observed_hours(value) -> str:
    return "Not recorded — inputs missing or unconfirmed" if value is None else f"{value:.2f} person-hours"


def comparison_row(assessment: dict) -> dict:
    estimate = estimate_opportunity(assessment)
    pilot = evaluate_pilot(assessment)
    return {
        "ID": assessment["id"],
        "Opportunity": assessment["title"],
        "Type": "Fictional example" if assessment.get("is_example") else "Assessment",
        "Recommended solution": assessment["solution_pattern"],
        "Preliminary readiness": estimate["readiness"],
        "Net weekly effort savings": hours_range(estimate["net_hours_per_week"]),
        "One-time implementation": hours_range(estimate["implementation_hours"]),
        "Scope": (assessment.get("effort_assumptions") or {}).get("scope") or "Not provided",
        "Missing / invalid inputs": "; ".join(estimate["missing_inputs"] + estimate["input_errors"]) or "None",
        "Pilot outcome": pilot["status"],
        "Observed total weekly effort": observed_hours(pilot["net_effort_hours_per_week"]),
        "Observed net weekly savings": observed_hours(pilot["net_savings_hours_per_week"]),
        "Pilot quality": pilot["quality_outcome"],
        "Pilot comparison": pilot["comparison"],
        "Saved pilot scenario savings": hours_range(pilot["scenario_net_hours_per_week"]),
        "Observed scope": (assessment.get("pilot_observation") or {}).get("scope") or "Not provided",
    }


def assessment_as_text(assessment: dict) -> str:
    estimate = estimate_opportunity(assessment)
    pilot = evaluate_pilot(assessment)
    sections = [
        ("Preliminary AI Compass assessment", assessment.get("title", "Opportunity")),
        ("Recommended pattern", assessment.get("solution_pattern", "")),
        ("Why this fits", assessment.get("explanation", "")),
        ("Alternatives", assessment.get("alternatives", [])),
        ("Potential benefits", assessment.get("benefits", [])),
        ("Missing information", assessment.get("missing_information", [])),
        ("Readiness concerns", assessment.get("readiness_concerns", [])),
        ("Recommended next steps", assessment.get("next_steps", [])),
        ("Preliminary readiness", estimate["readiness"]),
        ("Readiness checks", [f"{check['check']}: {check['status']}" for check in estimate["readiness_checks"]]),
        ("Net weekly effort savings", hours_range(estimate["net_hours_per_week"])),
        ("Gross weekly effort reduction before additional overhead", hours_range(estimate["gross_hours_per_week"])),
        ("One-time implementation", hours_range(estimate["implementation_hours"])),
        ("Estimate missing inputs", estimate["missing_inputs"]),
        ("Estimate input errors", estimate["input_errors"]),
        ("Calculation method", estimate["method"]),
        ("Estimate limitations", estimate["caveat"]),
        ("User-supplied estimate assumptions", json.dumps(assessment.get("effort_assumptions") or {}, indent=2)),
        ("Pilot observed outcome", pilot["status"]),
        ("Observed total weekly effort", observed_hours(pilot["net_effort_hours_per_week"])),
        ("Observed net weekly savings (negative means additional effort)", observed_hours(pilot["net_savings_hours_per_week"])),
        ("Saved preliminary scenario savings", hours_range(pilot["scenario_net_hours_per_week"])),
        ("Pilot comparison", pilot["comparison"]),
        ("Observed quality outcome", pilot["quality_outcome"]),
        ("Pilot missing inputs", pilot["missing_inputs"]),
        ("Pilot input errors", pilot["input_errors"]),
        ("Pilot calculation method", pilot["method"]),
        ("Pilot limitations", pilot["caveat"]),
        ("Recorded pilot evidence and saved scenario", json.dumps(assessment.get("pilot_observation") or {}, indent=2)),
    ]
    insight = assessment.get("ai_insight")
    if insight:
        sections.extend([
            ("AI interpretation", insight["summary"]),
            ("AI-proposed pilot plan", insight["pilot_plan"]),
            ("AI model", insight["model"]),
        ])
    output = []
    for heading, content in sections:
        output.append(f"{heading}\n" + ("-" * len(heading)))
        if isinstance(content, list):
            output.extend(f"- {item}" for item in content or ["None identified"])
        else:
            output.append(str(content))
        output.append("")
    output.append("This is a preliminary result and requires validation.")
    return "\n".join(output)


def assessment_as_json(assessment: dict) -> str:
    return json.dumps({**assessment, "preliminary_estimate": estimate_opportunity(assessment),
                       "pilot_result": evaluate_pilot(assessment)},
                      indent=2, ensure_ascii=False)

