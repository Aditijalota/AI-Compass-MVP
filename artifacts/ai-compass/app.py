"""AI Compass: a small, explainable AI opportunity discovery prototype."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from classification import classify
from database import get_assessment, initialize_database, list_assessments, save_assessment
from discovery import DEPARTMENTS, QUESTIONS, SCALES, suggested_opportunities
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
        "Recommendations are preliminary and need validation."
    )

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
                    st.session_state.intake_choice = path
                    st.session_state.suggestions = []
                    st.rerun()

    path = st.session_state.get("intake_choice")
    if not path:
        st.markdown("---")
        st.markdown("#### What happens next")
        st.write("A short six-part discovery, a transparent rules-based fit assessment, and a dashboard of saved opportunities.")
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
            department = st.selectbox("Department", DEPARTMENTS)
            role = st.text_input("Your role (optional)")
            problem = st.text_area(
                "What problem or inefficient process would you like to improve?",
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
            department = st.selectbox("Department", DEPARTMENTS)
            role = st.text_input("Role (optional)")
            submitted = st.form_submit_button("Show three opportunities", type="primary")
        if submitted:
            st.session_state.selected_department = department
            st.session_state.selected_role = role
            st.session_state.draft["intake_path"] = "explore"
            st.session_state.suggestions = suggested_opportunities(department, role)
            st.rerun()
        _show_opportunity_choices(st.session_state.suggestions)

    else:
        with st.form("new_to_ai_intake"):
            department = st.selectbox("Department", DEPARTMENTS)
            role = st.text_input("Your role")
            responsibilities = st.text_area(
                "What do you spend time doing in a typical week?",
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
                st.session_state.suggestions = suggested_opportunities(department, role, responsibilities)
                st.rerun()
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
    assessment_id = save_assessment(assessment.to_dict())
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
                index=SCALES.index(draft.get("problem_scale", "Individual")),
            )
            values["rollout_scale"] = st.selectbox(
                "Intended rollout scale",
                SCALES,
                index=SCALES.index(draft.get("rollout_scale", "Department")),
            )
        for key, label, placeholder in question["fields"]:
            values[key] = st.text_area(
                label,
                value=draft.get(key, ""),
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
    st.caption("No external business-system connections. LLM is not required.")

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
