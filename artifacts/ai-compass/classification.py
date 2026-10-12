"""Explainable rules for matching a process to a proportionate solution."""

from models import Assessment


def _contains(text: str, phrases: tuple[str, ...]) -> bool:
    text = text.lower()
    return any(phrase in text for phrase in phrases)


def classify(discovery: dict, now: str, assessment_id: int | None = None) -> Assessment:
    problem = discovery.get("business_problem", "").strip()
    content = " ".join(
        str(discovery.get(key, "")) for key in (
            "business_problem", "desired_outcome", "activities", "manual_work",
            "tools", "data_types", "rules", "exceptions", "business_impact",
        )
    ).lower()
    data_text = str(discovery.get("data_types", "")).lower()
    rules_text = str(discovery.get("rules", "")).lower()
    exception_text = str(discovery.get("exceptions", "")).lower()
    tools_text = str(discovery.get("tools", "")).lower()

    doc_signals = (
        "document", "documents", "pdf", "policy", "policies", "knowledge",
        "manual", "guide", "email", "emails", "unstructured",
    )
    repetitive_signals = (
        "repetitive", "copy", "copying", "repeat", "routine", "standard",
        "same steps", "manual entry", "sort", "sorting", "route",
    )
    human_signals = ("approval", "approve", "review", "exception", "judgment", "judgement")
    tool_signals = ("crm", "spreadsheet", "ticket", "workflow", "assistant", "copilot", "automation")
    multi_step_signals = ("multiple systems", "across systems", "end to end", "end-to-end", "multi-step")

    # "Manual work" alone is not evidence of document handling.
    doc_heavy = _contains(
        data_text,
        ("document", "pdf", "policy", "policies", "knowledge", "manuals", "guide", "email", "unstructured", "article"),
    )
    knowledge_lookup = doc_heavy and _contains(
        problem + " " + str(discovery.get("desired_outcome", "")),
        ("search", "lookup", "look up", "find answers", "find relevant", "guidance", "knowledge"),
    )
    repetitive = _contains(content, repetitive_signals)
    human_review = _contains(rules_text + " " + exception_text, human_signals)
    existing_tools = _contains(tools_text, tool_signals)
    has_exceptions = bool(exception_text.strip()) and exception_text.strip().lower() not in {
        "none", "no", "n/a", "not sure",
    }
    explicitly_multi_step = _contains(content, multi_step_signals)
    candidate_for_agent = explicitly_multi_step and has_exceptions and human_review

    if knowledge_lookup:
        pattern = "RAG / knowledge assistant"
        explanation = (
            "The main need is finding answers in approved documents. First check whether an "
            "existing approved search or AI tool can do this. If not, a retrieval-based "
            "assistant grounded in maintained sources may fit; autonomous action is not needed."
        )
        alternatives = ["Existing software or AI assistant", "Process improvement", "Hybrid solution"]
    elif doc_heavy and repetitive:
        pattern = "Hybrid solution"
        explanation = (
            "This combines recurring process work with document or knowledge handling. "
            "A controlled knowledge assistant can support the information task, while "
            "simple workflow automation can handle predictable steps."
        )
        alternatives = ["RAG / knowledge assistant", "AI-assisted automation", "Process improvement"]
    elif doc_heavy:
        pattern = "RAG / knowledge assistant"
        explanation = (
            "The discovery points to finding or interpreting information in documents. "
            "A retrieval-based assistant grounded in approved sources is a better first fit "
            "than an autonomous agent."
        )
        alternatives = ["Existing software or AI assistant", "Process improvement", "AI-assisted automation"]
    elif candidate_for_agent:
        pattern = "Agentic AI candidate"
        explanation = (
            "The process appears to span multiple steps or systems and includes exceptions. "
            "An agent may be worth a bounded pilot, but only with tool permissions, explicit "
            "approval gates, logging, and a human fallback. This is a candidate, not a default."
        )
        alternatives = ["AI-assisted automation", "Rule-based automation", "Process improvement"]
    elif repetitive and human_review and not has_exceptions:
        pattern = "Rule-based automation"
        explanation = (
            "The work is repetitive and appears to follow stable rules. Start with workflow "
            "automation; keep any existing approval step intact."
        )
        alternatives = ["Existing software or AI assistant", "Process improvement", "AI-assisted automation"]
    elif repetitive and (doc_heavy or has_exceptions or _contains(content, ("write", "draft", "summarize", "classify"))):
        pattern = "AI-assisted automation"
        explanation = (
            "The process has repeatable steps plus content that may vary. AI can assist with "
            "drafting, extraction, or classification, while a person verifies uncertain or "
            "high-impact outputs."
        )
        alternatives = ["Rule-based automation", "Existing software or AI assistant", "Process improvement"]
    elif existing_tools or _contains(content, ("already have", "existing system", "built-in")):
        pattern = "Existing software or AI assistant"
        explanation = (
            "The need may fit capabilities already available in current tools. Check existing "
            "software and approved AI features before buying or building anything custom."
        )
        alternatives = ["Process improvement", "Rule-based automation", "AI-assisted automation"]
    elif repetitive:
        pattern = "Rule-based automation"
        explanation = (
            "The described work is repeatable and does not yet show a clear need for generative "
            "AI. First verify whether the steps can be simplified or automated with fixed rules."
        )
        alternatives = ["Process improvement", "Existing software or AI assistant", "AI-assisted automation"]
    else:
        pattern = "Process improvement"
        explanation = (
            "There is not enough evidence that AI or automation is needed. Map the current "
            "process, remove avoidable steps, and clarify the desired outcome before selecting technology."
        )
        alternatives = ["Existing software or AI assistant", "Rule-based automation", "AI-assisted automation"]

    missing = []
    required = {
        "department": "Department",
        "role": "Role",
        "business_problem": "Specific problem or opportunity",
        "activities": "Current process steps",
        "tools": "Tools and systems involved",
        "data_types": "Data and document types",
        "rules": "Rules and approvals",
        "exceptions": "Exception handling and human decisions",
        "time_spent": "Estimated time spent",
        "security_concerns": "Data sensitivity and security constraints",
    }
    for key, label in required.items():
        if not str(discovery.get(key, "")).strip():
            missing.append(label)

    readiness = []
    security = discovery.get("security_concerns", "").lower()
    if _contains(security, ("sensitive", "personal", "confidential", "regulated", "customer data")):
        readiness.append("Confirm data handling, access controls, retention, and approved tools before using real information.")
    if human_review or has_exceptions:
        readiness.append("Keep a named person responsible for approvals and exceptions.")
    if not str(discovery.get("time_spent", "")).strip():
        readiness.append("Measure a baseline before estimating benefits or return on investment.")
    if pattern == "Agentic AI candidate":
        readiness.append("Do not grant broad or unsupervised system access during an initial pilot.")
    if not readiness:
        readiness.append("Validate the process with the people who perform it and confirm an owner for the next step.")

    benefits = []
    if repetitive:
        benefits.append("Reduce time spent on recurring manual steps.")
    if doc_heavy:
        benefits.append("Make relevant information easier to find and apply consistently.")
    if human_review or has_exceptions:
        benefits.append("Keep human judgment focused on exceptions and consequential decisions.")
    benefits.append("Create a clearer baseline for measuring process quality and effort.")

    next_steps = [
        "Validate the current process and pain points with the people doing the work.",
        "Check existing approved software before choosing a custom solution.",
        "Define a small pilot, success measure, owner, and human review path.",
    ]
    if pattern in ("RAG / knowledge assistant", "Hybrid solution"):
        next_steps.insert(1, "Identify a small, approved set of source documents and an owner to keep them current.")
    if pattern == "Agentic AI candidate":
        next_steps.insert(1, "Test the simplest alternative first; if an agent remains justified, define strict permissions and approval gates.")

    title = problem[:90] if problem else f"{discovery.get('department', 'Business')} opportunity"
    return Assessment(
        id=assessment_id,
        created_at=now,
        title=title,
        department=discovery.get("department", "Other") or "Other",
        role=discovery.get("role", ""),
        problem_scale=discovery.get("problem_scale", "Individual") or "Individual",
        rollout_scale=discovery.get("rollout_scale", "Department") or "Department",
        solution_pattern=pattern,
        explanation=explanation,
        alternatives=alternatives,
        benefits=benefits,
        missing_information=missing,
        readiness_concerns=readiness,
        next_steps=next_steps,
        discovery=discovery.copy(),
    )
