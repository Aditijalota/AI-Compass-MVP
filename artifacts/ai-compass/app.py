"""AI Compass: a small, explainable AI opportunity discovery prototype."""

from datetime import datetime, timezone
import sqlite3

import pandas as pd
import streamlit as st

from classification import classify
from database import get_assessment, initialize_database, list_assessments, save_assessment
from database import (
    save_discovery_draft, list_discovery_drafts, get_discovery_draft,
    discard_discovery_draft,
)
from draft_state import empty_draft, restore_state
from demo_examples import DEMOS
from llm_demo import AIUnavailable, MODEL, configured, opportunities, assessment_insight
from reports import assessment_as_json, assessment_as_text
from comparison_ui import render_comparison, render_effort_assumptions
from discovery import (
    AI_MODEL, DEPARTMENTS, MAX_INPUT_CHARS, QUESTIONS, SCALES,
    ai_available, discovery_prompt, prompt_cache_key, suggested_opportunities,
)

st.set_page_config(page_title="AI Compass", layout="wide")


def _empty_draft():
    return empty_draft()


def _initialize_state():
    defaults = {
        "page": "Welcome",
        "draft": _empty_draft(),
        "step": 0,
        "suggestions": [],
        "assessment_id": None,
        "assessment": None,
        "discovery_prompts": {},
        "saved_exchanges": set(),
        "demo_path": None,
        "active_draft_id": None,
        "draft_storage_authorized": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _begin_discovery(path: str, department: str, role: str, problem: str = "", activities: str = ""):
    for key in list(st.session_state):
        if key.startswith("step_"):
            del st.session_state[key]
    st.session_state.active_draft_id = None
    st.session_state.draft_storage_authorized = False
    draft = _empty_draft()
    draft.update({
        "intake_path": path,
        "department": department or "Other",
        "role": role.strip(),
        "business_problem": problem.strip(),
        "activities": activities.strip(),
        "problem_scale": _demo().get("problem_scale", draft["problem_scale"]),
        "rollout_scale": _demo().get("rollout_scale", draft["rollout_scale"]),
    })
    st.session_state.draft = draft
    st.session_state.step = 0
    st.session_state.page = "Discovery Studio"
    st.session_state.assessment = None
    st.session_state.assessment_id = None
    st.session_state.discovery_prompts = {}
    st.session_state.saved_exchanges = set()
    # Consent and model use never carry over to a new discovery.
    st.session_state.ai_discovery = False
    st.session_state.ai_authorized = False
    st.rerun()


def _resume_draft(draft_id):
    try:
        restore_state(st.session_state, get_discovery_draft(draft_id))
        st.session_state.draft_notice = "Draft resumed. AI is off; opt in and confirm inputs again before using any AI feature."
    except (sqlite3.Error, ValueError, KeyError, TypeError) as error:
        st.session_state.draft_error = f"Could not resume draft: {error}"


def _discard_draft(draft_id):
    try:
        discard_discovery_draft(draft_id)
        if st.session_state.active_draft_id == draft_id:
            st.session_state.active_draft_id = None
        st.session_state.draft_notice = "Saved draft deleted. Any answers currently open in this session are unchanged."
        st.session_state.discard_draft_confirm = False
    except sqlite3.Error as error:
        st.session_state.draft_error = f"Could not discard draft: {error}"


def _draft_controls():
    with st.expander("Resume or discard a saved draft"):
        st.warning(
            "Shared prototype storage, not private user storage: anyone with access to this "
            "app can resume or delete these drafts. Save fictional or authorized non-sensitive "
            "information only. Do not save personal, client-sensitive, or confidential data."
        )
        st.caption(
            "Resume replaces the discovery open in this session; save it first if needed. "
            "Only explicitly saved answers and progress survive a lost session. AI consent is never stored."
        )
        try:
            drafts = list_discovery_drafts()
        except sqlite3.Error as error:
            st.error(f"Could not load saved drafts: {error}")
            return
        if not drafts:
            st.caption("No saved discovery drafts yet.")
            return
        labels = {f"Draft #{item['id']} · saved {item['updated_at']}": item["id"] for item in drafts}
        def _reset_discard_confirmation():
            st.session_state.discard_draft_confirm = False

        selected = st.selectbox(
            "Saved discovery draft", list(labels),
            on_change=_reset_discard_confirmation,
        )
        draft_id = labels[selected]
        st.button("Resume draft", on_click=_resume_draft, args=(draft_id,))
        confirmed = st.checkbox(
            "Delete the selected saved copy permanently (not any saved assessment).",
            key="discard_draft_confirm",
        )
        st.button("Discard saved draft", disabled=not confirmed, on_click=_discard_draft, args=(draft_id,))


def _demo():
    return DEMOS.get(st.session_state.demo_path, {})


def _opportunities(department, role, responsibilities=""):
    if not (st.session_state.use_ai and st.session_state.ai_enrichment_authorized):
        return suggested_opportunities(department, role, responsibilities)
    try:
        with st.spinner("AI is finding three starting points for your context…"):
            return opportunities(department, role, responsibilities)
    except AIUnavailable as error:
        st.error(str(error))
        return []


def _demo_controls():
    with st.expander("Fictional demos for recording"):
        st.caption("Load an example, then submit each exchange. All values remain editable; enable optional AI to show model-selected follow-ups.")
        for path, example in DEMOS.items():
            if st.button(f"Load: {example['name']}", key=f"load_demo_{path}"):
                for key in list(st.session_state):
                    if key.startswith("step_"):
                        del st.session_state[key]
                st.session_state.demo_path = path
                st.session_state.intake_choice = path
                st.session_state.page = "Welcome"
                st.session_state.draft = _empty_draft()
                st.session_state.active_draft_id = None
                st.session_state.draft_storage_authorized = False
                st.session_state.step = 0
                st.session_state.suggestions = []
                st.session_state.discovery_prompts = {}
                st.session_state.saved_exchanges = set()
                st.session_state.ai_discovery = False
                st.session_state.ai_authorized = False
                st.session_state.assessment = None
                st.session_state.assessment_id = None
                st.session_state.responsibilities = ""
                st.rerun()
        if st.session_state.demo_path:
            st.caption(_demo()["watch_for"])
            if st.button("Clear demo example"):
                st.session_state.demo_path = None
                st.session_state.intake_choice = None
                st.session_state.page = "Welcome"
                st.session_state.draft = _empty_draft()
                st.session_state.active_draft_id = None
                st.session_state.draft_storage_authorized = False
                st.session_state.suggestions = []
                st.session_state.discovery_prompts = {}
                st.session_state.saved_exchanges = set()
                st.session_state.ai_discovery = False
                st.session_state.ai_authorized = False
                st.session_state.assessment = None
                st.session_state.assessment_id = None
                for key in list(st.session_state):
                    if key.startswith("step_"):
                        del st.session_state[key]
                st.rerun()


def _show_opportunity_choices(opportunities, responsibilities=""):
    if not opportunities:
        return
    st.markdown("#### Choose an opportunity to assess")
    columns = st.columns(3)
    for index, opportunity in enumerate(opportunities):
        with columns[index]:
            with st.container(border=True):
                st.markdown(f"**{opportunity['title']}**")
                st.caption(opportunity["description"])
                if st.button("Assess this opportunity", key=f"choose_opportunity_{index}", use_container_width=True):
                    _begin_discovery(
                        path=st.session_state.draft.get("intake_path") or "explore",
                        department=opportunity["department"],
                        role=opportunity["role"],
                        problem=f"{opportunity['title']}: {opportunity['description']}",
                        activities=responsibilities,
                    )


def _welcome():
    st.title("AI Compass")
    st.subheader("Discover where AI can create value in your business.")
    st.write(
        "Explore AI opportunities, understand your business processes, and discover whether process improvement, "
        "existing AI tools, automation, or custom AI solutions are the right fit for your needs."
    )
    st.info(
        "Prototype notice: use fictional or authorized non-sensitive information only. "
        "Do not enter client secrets, personal data, or confidential business details. "
        "When AI is enabled, submitted descriptions are sent to the AI provider. "
        "Recommendations are preliminary and need validation."
    )
    if _demo():
        st.info(f"Recording demo: {_demo()['name']}. Fictional answers are prefilled; submit them exchange by exchange.")

    pathways = [
        ("problem", "I have a business problem", "Describe a current bottleneck or inefficient process."),
        ("explore", "Explore my department", "Start with common opportunities in a team or function."),
        ("new_to_ai", "I'm new to AI", "Use your role and daily responsibilities to find a place to start."),
    ]
    cards = st.columns(3)
    for column, (path, title, description) in zip(cards, pathways):
        with column:
            with st.container(border=True):
                st.markdown(f"### {title}")
                st.write(description)
                if st.button("Start here", key=f"path_{path}", use_container_width=True):
                    st.session_state.demo_path = None
                    st.session_state.intake_choice = path
                    st.session_state.suggestions = []
                    st.rerun()

    path = st.session_state.get("intake_choice")
    if not path:
        st.markdown("---")
        st.markdown("#### What happens next")
        st.write("Six answer-aware discovery exchanges, a transparent rules-based assessment, optional AI assistance, and saved opportunities.")
        return

    st.markdown("---")
    st.subheader({
        "problem": "Start with the business problem",
        "explore": "Choose a department to explore",
        "new_to_ai": "Start with your role and responsibilities",
    }[path])
    if st.button("← Choose a different pathway", key="back_to_pathways"):
        st.session_state.pop("intake_choice", None)
        st.session_state.suggestions = []
        st.rerun()

    if path == "problem":
        with st.form("business_problem_intake"):
            department = st.selectbox("Department", DEPARTMENTS, index=DEPARTMENTS.index(_demo().get("department", "Finance")))
            role = st.text_input("Your role (optional)", value=_demo().get("role", ""), max_chars=MAX_INPUT_CHARS)
            problem = st.text_area(
                "What problem or inefficient process would you like to improve?",
                value=_demo().get("business_problem", ""),
                placeholder="Keep it high-level; use fictional or non-sensitive details.",
                height=120,
                max_chars=MAX_INPUT_CHARS,
            )
            submitted = st.form_submit_button("Continue to discovery", type="primary")
        if submitted:
            if not problem.strip():
                st.warning("Add a short description of the problem to continue.")
            else:
                _begin_discovery("problem", department, role, problem)

    elif path == "explore":
        with st.form("department_intake"):
            department = st.selectbox("Department", DEPARTMENTS, index=DEPARTMENTS.index(_demo().get("department", "Finance")))
            role = st.text_input("Role (optional)", value=_demo().get("role", ""), max_chars=MAX_INPUT_CHARS)
            submitted = st.form_submit_button("Show three opportunities", type="primary")
        if submitted:
            st.session_state.selected_department = department
            st.session_state.selected_role = role
            st.session_state.draft["intake_path"] = "explore"
            st.session_state.suggestions = _opportunities(department, role)
            if st.session_state.suggestions:
                st.rerun()
        if any(item.get("ai_model") for item in st.session_state.suggestions):
            st.caption(f"Three AI-generated opportunities · {MODEL}")
        _show_opportunity_choices(st.session_state.suggestions)

    else:
        with st.form("new_to_ai_intake"):
            department = st.selectbox("Department", DEPARTMENTS, index=DEPARTMENTS.index(_demo().get("department", "Finance")))
            role = st.text_input("Your role", value=_demo().get("role", ""), max_chars=MAX_INPUT_CHARS)
            responsibilities = st.text_area(
                "What do you spend time doing in a typical week?",
                value=_demo().get("activities", ""),
                placeholder="For example: review requests, prepare reports, answer recurring questions.",
                height=120,
                max_chars=MAX_INPUT_CHARS,
            )
            submitted = st.form_submit_button("Suggest starting points", type="primary")
        if submitted:
            if not role.strip() and not responsibilities.strip():
                st.warning("Add a role or a few responsibilities so the suggestions have some context.")
            else:
                st.session_state.responsibilities = responsibilities
                st.session_state.draft["intake_path"] = "new_to_ai"
                st.session_state.suggestions = _opportunities(department, role, responsibilities)
                if st.session_state.suggestions:
                    st.rerun()
        if any(item.get("ai_model") for item in st.session_state.suggestions):
            st.caption(f"Three AI-generated opportunities · {MODEL}")
        _show_opportunity_choices(
            st.session_state.suggestions,
            responsibilities=st.session_state.get("responsibilities", ""),
        )


def _save_preliminary_assessment():
    draft = st.session_state.draft.copy()
    assessment = classify(
        draft,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    payload = assessment.to_dict()
    payload["is_example"] = bool(st.session_state.demo_path)
    if st.session_state.use_ai and st.session_state.ai_enrichment_authorized:
        try:
            with st.spinner("AI is explaining your solution fit and drafting a bounded pilot plan…"):
                payload["ai_insight"] = assessment_insight(payload)
        except AIUnavailable as error:
            st.error(str(error))
            st.info("No assessment was saved. Retry, or disable AI to explicitly save a rules-only assessment.")
            return
    assessment_id = save_assessment(payload)
    st.session_state.assessment_id = assessment_id
    st.session_state.assessment = get_assessment(assessment_id)
    st.session_state.page = "Assessment"
    st.rerun()


def _render_discovery_step(index: int):
    question = QUESTIONS[index]
    draft = st.session_state.draft
    st.markdown(f"### Exchange {index + 1} of {len(QUESTIONS)} · {question['title']}")
    use_ai = st.session_state.get("ai_discovery", False)
    authorized = st.session_state.get("ai_authorized", False)
    cache_key = prompt_cache_key(index, draft, use_ai, authorized)
    cache = st.session_state.discovery_prompts
    if cache_key not in cache:
        with st.spinner("Preparing the next question…"):
            cache[cache_key] = discovery_prompt(index, draft, use_ai=use_ai, authorized=authorized)
    prompt = cache[cache_key]
    st.caption(
        f"AI-selected follow-up · OpenAI {AI_MODEL} via Replit AI Integrations"
        if prompt.source == "ai" else "Answer-aware guided follow-up · no model used for this question"
    )
    if prompt.notice:
        st.warning(prompt.notice)
    st.write(prompt.text)
    with st.form(f"discovery_step_{index}"):
        values = {}
        if index == 0:
            values["department"] = st.selectbox(
                "Department",
                DEPARTMENTS,
                index=DEPARTMENTS.index(draft.get("department", "Other")),
                key="step_0_department",
            )
            values["role"] = st.text_input("Role", value=draft.get("role", ""), max_chars=MAX_INPUT_CHARS, key="step_0_role")
            values["problem_scale"] = st.selectbox(
                "Current problem scale",
                SCALES,
                index=SCALES.index(draft.get("problem_scale", "Individual")),
                key="step_0_problem_scale",
            )
            values["rollout_scale"] = st.selectbox(
                "Intended rollout scale",
                SCALES,
                index=SCALES.index(draft.get("rollout_scale", "Department")),
                key="step_0_rollout_scale",
            )
        for key, label, placeholder in question["fields"]:
            values[key] = st.text_area(
                label,
                value=draft.get(key, "") or _demo().get(key, ""),
                placeholder=placeholder,
                height=90,
                key=f"step_{index}_{key}",
                max_chars=MAX_INPUT_CHARS,
            )
        submitted = st.form_submit_button(
            "Save exchange and continue" if index < len(QUESTIONS) - 1 else "Save final exchange",
            type="primary",
            use_container_width=True,
        )
        save_draft = st.form_submit_button(
            "Save draft for later",
            disabled=not st.session_state.draft_storage_authorized,
            use_container_width=True,
        )
    if save_draft:
        draft.update(values)
        try:
            st.session_state.active_draft_id = save_discovery_draft(
                draft, index, st.session_state.saved_exchanges,
                st.session_state.demo_path, st.session_state.active_draft_id,
            )
            st.success(
                f"Draft #{st.session_state.active_draft_id} saved, including this exchange's "
                "current fields. Resume it from the sidebar after a refresh. "
                "Later edits are not saved automatically."
            )
        except (sqlite3.Error, ValueError) as error:
            st.error(f"Draft was not saved: {error}")
    if submitted:
        draft.update(values)
        st.session_state.draft = draft
        st.session_state.saved_exchanges.add(index)
        st.session_state.step = min(index + 1, len(QUESTIONS) - 1)
        st.rerun()


def _discovery():
    st.title("Discovery Studio")
    st.caption("Six short exchanges to understand the work before considering technology.")
    st.warning("Keep descriptions high-level. Do not include confidential, personal, or client-sensitive information.")
    st.checkbox(
        "I confirm this draft contains only fictional or authorized non-sensitive information "
        "and may be saved in shared prototype storage.",
        key="draft_storage_authorized",
    )
    st.caption(
        "Save draft for later stores the current fields and exchange progress locally. "
        "Save exchange and continue only updates this session; save the draft again to retain later changes. "
        "AI permissions and generated questions are not stored."
    )
    with st.expander("Optional AI discovery", expanded=False):
        st.write(
            f"AI uses OpenAI {AI_MODEL} through Replit AI Integrations to select a follow-up "
            "from a reviewed set for each exchange. No API key is required; usage is billed "
            "to Replit credits. Only high-level saved intake and prior answers (up to 600 "
            "characters per field) are sent to the model when you opt in. "
            "Questions are kept in this session, not saved with the assessment. "
            "AI never changes the rules-based classifier or connects to business systems."
        )
        if not ai_available():
            st.info("Replit AI Integrations is not configured here. Guided discovery remains fully available.")
        st.checkbox(
            "I confirm my saved inputs are fictional or authorized non-sensitive information.",
            key="ai_authorized",
        )
        st.toggle("Use AI to select follow-up questions", key="ai_discovery")
    st.caption("Guided mode works without an LLM. You can turn AI off at any time; your answers are preserved.")
    if len(st.session_state.saved_exchanges) == len(QUESTIONS):
        st.success("All six exchanges are saved. Generate your preliminary assessment below.")
    progress = (st.session_state.step + 1) / len(QUESTIONS)
    st.progress(progress, text=f"Exchange {st.session_state.step + 1} of {len(QUESTIONS)}")
    _render_discovery_step(st.session_state.step)

    back_col, spacer, assess_col = st.columns([1, 2, 1])
    with back_col:
        if st.session_state.step > 0 and st.button("← Previous exchange", use_container_width=True):
            st.session_state.step -= 1
            st.rerun()
    with assess_col:
        if st.button("Generate preliminary assessment", type="primary", use_container_width=True):
            _save_preliminary_assessment()

    with st.expander("What you've shared so far"):
        for label, key in [
            ("Problem", "business_problem"),
            ("Department", "department"),
            ("Role", "role"),
            ("Current process", "activities"),
            ("Tools", "tools"),
        ]:
            value = st.session_state.draft.get(key) or "Not provided yet"
            st.markdown(f"**{label}:** {value}")


def _bullet_section(title: str, values):
    st.markdown(f"#### {title}")
    if values:
        for value in values:
            st.markdown(f"- {value}")
    else:
        st.write("None identified yet.")


def _assessment_detail(assessment: dict):
    st.title("Preliminary solution fit")
    st.caption("This rules-based recommendation is a starting point, not a validated business case.")
    if assessment.get("is_example"):
        st.info("Fictional example assessment")
    st.subheader(assessment.get("title", "Opportunity"))
    st.write(
        f"**Department:** {assessment.get('department', 'Other')}  ·  "
        f"**Current scale:** {assessment.get('problem_scale', 'Not specified')}  ·  "
        f"**Intended rollout:** {assessment.get('rollout_scale', 'Not specified')}"
    )
    st.markdown("### Recommended pattern")
    st.success(assessment.get("solution_pattern", "Process improvement"))
    st.write(assessment.get("explanation", ""))
    if assessment.get("ai_insight"):
        insight = assessment["ai_insight"]
        st.markdown("### AI interpretation of your answers")
        st.caption(f"Generated by {insight['model']}. The transparent rules above determine the recommended pattern.")
        st.write(insight["summary"])
        _bullet_section("AI-proposed pilot plan", insight["pilot_plan"])
    left, right = st.columns(2)
    with left:
        _bullet_section("Alternative approaches", assessment.get("alternatives", []))
        _bullet_section("Potential benefits", assessment.get("benefits", []))
    with right:
        _bullet_section("Missing information", assessment.get("missing_information", []))
        _bullet_section("Readiness concerns", assessment.get("readiness_concerns", []))
    _bullet_section("Recommended next steps", assessment.get("next_steps", []))
    render_effort_assumptions(assessment)
    st.markdown("---")
    st.caption("Validate with process owners before making technical, operational, or investment decisions.")
    text_col, json_col = st.columns(2)
    filename = f"ai-compass-assessment-{assessment.get('id', 'draft')}"
    with text_col:
        st.download_button(
            "Download readable summary",
            assessment_as_text(assessment),
            file_name=f"{filename}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with json_col:
        st.download_button(
            "Download assessment data",
            assessment_as_json(assessment),
            file_name=f"{filename}.json",
            mime="application/json",
            use_container_width=True,
        )
    if st.button("← Return to dashboard", key="assessment_to_dashboard"):
        st.session_state.page = "Opportunity Dashboard"
        st.rerun()


def _dashboard():
    st.title("Opportunity Dashboard")
    st.write("Saved discovery assessments, including three clearly marked fictional examples.")
    assessments = list_assessments()
    if not assessments:
        st.info("No assessments have been saved yet. Start a discovery to create one.")
        return
    frame = pd.DataFrame([
        {
            "ID": item["id"],
            "Opportunity": item["title"],
            "Department": item["department"],
            "Current scale": item["problem_scale"],
            "Recommended solution": item["solution_pattern"],
            "Type": "Fictional example" if item.get("is_example") else "Assessment",
            "Created": item["created_at"][:10],
        }
        for item in assessments
    ])
    metric_cols = st.columns(3)
    metric_cols[0].metric("Opportunities discovered", len(frame))
    metric_cols[1].metric("Departments", frame["Department"].nunique())
    metric_cols[2].metric("Solution patterns", frame["Recommended solution"].nunique())

    distribution_cols = st.columns(3)
    with distribution_cols[0]:
        st.markdown("#### By department")
        st.bar_chart(frame["Department"].value_counts().sort_values(ascending=False))
    with distribution_cols[1]:
        st.markdown("#### By current scale")
        st.bar_chart(frame["Current scale"].value_counts().sort_values(ascending=False))
    with distribution_cols[2]:
        st.markdown("#### By solution pattern")
        st.bar_chart(frame["Recommended solution"].value_counts().sort_values(ascending=False))

    st.markdown("### Search assessments")
    query = st.text_input("Search by opportunity, department, scale, or recommendation", key="dashboard_search")
    visible = frame
    if query.strip():
        mask = frame.astype(str).apply(
            lambda column: column.str.contains(query.strip(), case=False, na=False, regex=False)
        ).any(axis=1)
        visible = frame[mask]
    st.dataframe(visible, hide_index=True, use_container_width=True)
    if visible.empty:
        st.info("No assessments match that search.")
        return

    options = {
        f"#{row['ID']} · {row['Opportunity']} — {row['Recommended solution']}": int(row["ID"])
        for _, row in visible.iterrows()
    }
    render_comparison([item for item in assessments if item["id"] in set(options.values())])
    selected_label = st.selectbox("Choose an assessment to reopen", list(options))
    if st.button("Reopen assessment", type="primary"):
        st.session_state.assessment_id = options[selected_label]
        st.session_state.assessment = get_assessment(options[selected_label])
        st.session_state.page = "Assessment"
        st.rerun()


initialize_database()
_initialize_state()

with st.sidebar:
    st.title("AI Compass")
    st.caption("Opportunity discovery · v0.1")
    destinations = ["Welcome", "Discovery Studio", "Opportunity Dashboard"]
    if st.session_state.page in destinations:
        st.session_state.navigation = st.session_state.page

    def _navigate():
        st.session_state.page = st.session_state.navigation

    st.radio(
        "Navigate",
        destinations,
        key="navigation",
        on_change=_navigate,
    )
    st.markdown("---")
    _draft_controls()
    if st.session_state.get("draft_notice"):
        st.success(st.session_state.pop("draft_notice"))
    if st.session_state.get("draft_error"):
        st.error(st.session_state.pop("draft_error"))
    st.checkbox(
        "My inputs for AI suggestions and explanations are fictional or authorized and non-sensitive.",
        key="ai_enrichment_authorized",
    )
    st.toggle("Use AI opportunities and assessment explanations", value=False, key="use_ai")
    st.caption("Discovery follow-up AI is enabled separately in Discovery Studio.")
    if st.session_state.use_ai and st.session_state.ai_enrichment_authorized:
        if configured():
            st.caption(f"AI enabled · OpenAI {MODEL}")
            st.caption("AI usage is billed to Replit credits. Submit only fictional or authorized non-sensitive descriptions.")
        else:
            st.error("AI access is not configured.")
    else:
        st.caption("Local opportunity suggestions and rules-based assessment. No model used for these features.")
        if st.session_state.use_ai:
            st.info("Confirm non-sensitive inputs above before AI suggestions or assessment explanations can be used.")
    st.caption("No external business-system connections. No autonomous actions.")
    _demo_controls()

if st.session_state.page == "Welcome":
    _welcome()
elif st.session_state.page == "Discovery Studio":
    _discovery()
elif st.session_state.page == "Opportunity Dashboard":
    _dashboard()
else:
    assessment = st.session_state.assessment
    if not assessment and st.session_state.assessment_id:
        assessment = get_assessment(st.session_state.assessment_id)
    if assessment:
        _assessment_detail(assessment)
    else:
        st.error("Assessment could not be found.")
        st.session_state.page = "Opportunity Dashboard"
