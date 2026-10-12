"""Bounded discovery snapshots; permissions and model responses are never stored."""

from discovery import DEPARTMENTS, MAX_INPUT_CHARS, QUESTIONS, SCALES


def empty_draft():
    return {
        "intake_path": "", "department": "Other", "role": "",
        "problem_scale": "Individual", "rollout_scale": "Department",
        **{key: "" for question in QUESTIONS for key, _, _ in question["fields"]},
    }


def snapshot(draft, step, saved_exchanges, demo_path=None):
    """Allowlist fields and validate progress before storing or restoring."""
    fields = empty_draft()
    for key in fields:
        value = draft.get(key, fields[key])
        if not isinstance(value, str) or len(value) > MAX_INPUT_CHARS:
            raise ValueError("Draft fields must be bounded text.")
        fields[key] = value
    if fields["department"] not in DEPARTMENTS:
        raise ValueError("Draft department is not supported.")
    if any(fields[key] not in SCALES for key in ("problem_scale", "rollout_scale")):
        raise ValueError("Draft scale is not supported.")
    if fields["intake_path"] not in ("problem", "explore", "new_to_ai"):
        raise ValueError("Start a discovery before saving a draft.")
    if type(step) is not int or not 0 <= step < len(QUESTIONS):
        raise ValueError("Draft exchange is not supported.")
    exchanges = sorted(set(saved_exchanges))
    if any(type(index) is not int or not 0 <= index < len(QUESTIONS) for index in exchanges):
        raise ValueError("Draft progress is not supported.")
    if demo_path not in (None, "problem", "explore", "new_to_ai"):
        raise ValueError("Draft example is not supported.")
    return {
        "version": 1, "draft": fields, "step": step,
        "saved_exchanges": exchanges, "demo_path": demo_path,
    }


def restore_state(state, stored):
    """Called before widgets render so old widget values cannot replace answers."""
    if stored.get("version") != 1:
        raise ValueError("This draft format is not supported.")
    clean = snapshot(
        stored["draft"], stored["step"], stored["saved_exchanges"],
        stored.get("demo_path"),
    )
    for key in list(state):
        if key.startswith("step_"):
            del state[key]
    state.update({
        "draft": clean["draft"], "step": clean["step"],
        "saved_exchanges": set(clean["saved_exchanges"]),
        "demo_path": clean["demo_path"], "active_draft_id": stored["id"],
        "page": "Discovery Studio", "discovery_prompts": {}, "suggestions": [],
        "assessment": None, "assessment_id": None,
        "ai_discovery": False, "ai_authorized": False,
        "use_ai": False, "ai_enrichment_authorized": False,
        "draft_storage_authorized": False,
    })
