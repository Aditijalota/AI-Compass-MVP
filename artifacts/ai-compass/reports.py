"""Small export helpers used by the assessment detail screen."""

import json


def assessment_as_text(assessment: dict) -> str:
    sections = [
        ("Preliminary AI Compass assessment", assessment.get("title", "Opportunity")),
        ("Recommended pattern", assessment.get("solution_pattern", "")),
        ("Why this fits", assessment.get("explanation", "")),
        ("Alternatives", assessment.get("alternatives", [])),
        ("Potential benefits", assessment.get("benefits", [])),
        ("Missing information", assessment.get("missing_information", [])),
        ("Readiness concerns", assessment.get("readiness_concerns", [])),
        ("Recommended next steps", assessment.get("next_steps", [])),
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
    return json.dumps(assessment, indent=2, ensure_ascii=False)

