"""AI Compass: a small, explainable AI opportunity discovery prototype."""

from datetime import datetime, timezone
import hashlib
import json

import pandas as pd
import streamlit as st

from classification import classify
from database import get_assessment, initialize_database, list_assessments, save_assessment
from discovery import DEPARTMENTS, QUESTIONS, SCALES, suggested_opportunities
from demo_examples import DEMOS
from llm_demo import AIUnavailable, MODEL, configured, opportunities, next_question, assessment_insight
from reports import assessment_as_json, assessment_as_text


st.set_page_config(page_title="AI Compass", layout="wide")


def _empty_draft():
    return {
        "intake_path": "",
        "department": "Other",
        "role": "",
        "problem_scale": "Individual",
        "rollout_scale": "Department",
        "business_problem": "",
        "desired_outcome": "",
        "activities": "",
        "manual_work": "",
        "frequency": "",
        "tools": "",
        "data_types": "",
        "rules": "",
        "exceptions": "",
        "time_spent": "",
        "business_impact": "",
        "security_concerns": "",
        "constraints": "",
    }


def _initialize_state():
    defaults = {
        "page": "Welcome",
        "draft": _empty_draft(),
        "step": 0,
        "suggestions": [],
        "assessment_id": None,
        "assessment": None,
        "ai_questions": {},
        "demo_path": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _begin_discovery(path: str, department: str, role: str, problem: str = "", activities: str = ""):
    draft = _empty_draft()
    draft.update({
        "intake_path": path,
        "department": department or "Other",
        "role": role.strip(),
        "business_problem": problem.strip(),
        "activities": activities.strip(),
    })
    st.session_state.draft = draft
    st.session_state.step = 0
    st.session_state.page = "Discovery Studio"
    st.session_state.assessment = None
    st.session_state.assessment_id = None
    st.session_state.ai_questions = {}
    st.rerun()


def _demo():
    return DEMOS.get(st.session_state.demo_path, {})


def _opportunities(department, role, responsibilities=""):
    if not st.session_state.use_ai:
        return suggested_opportunities(department, role, responsibilities)
    try:
        with st.spinner("AI is finding three starting points for your context…"):
            return opportunities(department, role, responsibilities)
    except AIUnavailable as error:
        st.error(str(error))
        return []


def _demo_controls():
    with st.expander("Fictional demos for recording"):
        st.caption("Load an example, then submit each exchange to show the live AI adapting. All values remain editable.")
        for path, example in DEMOS.items():
            if st.button(f"Load: {example['name']}", key=f"load_demo_{path}"):
                for key in list(st.session_state):
                    if key.startswith("step_"):
                        del st.session_state[key]
                st.session_state.demo_path = path
                st.session_state.intake_choice = path
                st.session_state.page = "Welcome"
                st.session_state.draft = _empty_draft()
                st.session_state.step = 0
                st.session_state.suggestions = []
                st.session_state.ai_questions = {}
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
                st.session_state.suggestions = []
                st.session_state.ai_questions = {}
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
    st.subheader("Find the right-sized solution to a real work problem.")
    st.write(
        "Describe a process, explore opportunities in a department, or start with your day-to-day work. "
        "AI Compass guides you through discovery and explains why a simple process change, existing tool, "
        "automation, or AI approach may fit."
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
        st.write("Six AI-tailored discovery exchanges, a transparent fit assessment with an AI explanation, and saved opportunities.")
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
            role = st.text_input("Your role (optional)", value=_demo().get("role", ""))
            problem = st.text_area(
                "What problem or inefficient process would you like to improve?",
                value=_demo().get("business_problem", ""),
                placeholder="Keep it high-level; use fictional or non-sensitive details.",
                height=120,
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
            role = st.text_input("Role (optional)", value=_demo().get("role", ""))
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
            role = st.text_input("Your role", value=_demo().get("role", ""))
            responsibilities = st.text_area(
                "What do you spend time doing in a typical week?",
                value=_demo().get("activities", ""),
                placeholder="For example: review requests, prepare reports, answer recurring questions.",
                height=120,
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
    if st.session_state.use_ai:
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
    prompt = question["prompt"]
    if index == 0 and draft.get("department"):
        role_context = f" for a {draft['role']}" if draft.get("role") else ""
        prompt = f"Starting with {draft['department']}{role_context}: {prompt[0].lower() + prompt[1:]}"
    elif index == 1 and draft.get("business_problem"):
        prompt = f"For “{draft['business_problem'][:100]}”, {prompt[0].lower() + prompt[1:]}"
    if st.session_state.use_ai:
        fingerprint = hashlib.sha256(json.dumps(
            {"draft": draft, "index": index}, sort_keys=True
        ).encode()).hexdigest()
        cache = st.session_state.ai_questions
        if fingerprint not in cache:
            try:
                with st.spinner("AI is adapting the next question to your answers…"):
                    cache[fingerprint] = next_question(draft, question, index)
            except AIUnavailable as error:
                cache[fingerprint] = {"error": str(error)}
        generated = cache[fingerprint]
        if generated.get("error"):
            st.error(generated["error"])
            st.caption("Showing the standard question below. This exchange is not AI-generated.")
            if st.button("Retry AI question", key=f"retry_ai_{index}"):
                del cache[fingerprint]
                st.rerun()
        else:
            prompt = generated["prompt"]
            summary = generated.get("context_summary")
            if isinstance(summary, str) and summary:
                st.caption(summary)
            st.caption(f"AI-generated follow-up · {MODEL}")
    st.write(prompt)
    with st.form(f"discovery_step_{index}"):
        values = {}
        if index == 0:
            values["department"] = st.selectbox(
                "Department",
                DEPARTMENTS,
                index=DEPARTMENTS.index(draft.get("department", "Other")),
            )
            values["role"] = st.text_input("Role", value=draft.get("role", ""))
            values["problem_scale"] = st.selectbox(
                "Current problem scale",
                SCALES,
                index=SCALES.index(_demo().get("problem_scale", draft.get("problem_scale", "Individual"))),
            )
            values["rollout_scale"] = st.selectbox(
                "Intended rollout scale",
                SCALES,
                index=SCALES.index(_demo().get("rollout_scale", draft.get("rollout_scale", "Department"))),
            )
        for key, label, placeholder in question["fields"]:
            values[key] = st.text_area(
                label,
                value=draft.get(key, "") or _demo().get(key, ""),
                placeholder=placeholder,
                height=90,
                key=f"step_{index}_{key}",
            )
        submitted = st.form_submit_button(
            "Save exchange and continue" if index < len(QUESTIONS) - 1 else "Save final exchange",
            type="primary",
            use_container_width=True,
        )
    if submitted:
        draft.update(values)
        st.session_state.draft = draft
        st.session_state.step = min(index + 1, len(QUESTIONS) - 1)
        st.rerun()


def _discovery():
    st.title("Discovery Studio")
    st.caption("Six short exchanges to understand the work before considering technology.")
    st.warning("Keep descriptions high-level. Do not include confidential, personal, or client-sensitive information.")
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
    st.toggle("Use LLM-powered discovery", value=True, key="use_ai")
    if st.session_state.use_ai:
        if configured():
            st.caption(f"AI enabled · OpenAI {MODEL}")
            st.caption("AI usage is billed to Replit credits. Submit only fictional or authorized non-sensitive descriptions.")
        else:
            st.error("AI access is not configured.")
    else:
        st.caption("Guided mode · local questions and rules; no LLM calls.")
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
