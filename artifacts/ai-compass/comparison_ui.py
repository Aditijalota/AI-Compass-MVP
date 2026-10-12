"""Streamlit controls for explicit effort assumptions and opportunity comparison."""

import pandas as pd
import sqlite3
import streamlit as st

from classification import estimate_opportunity, evaluate_pilot
from database import get_assessment, update_effort_assumptions, update_pilot_observation
from models import EffortAssumptions, EFFORT_RANGES, READINESS_CHECKS, READINESS_STATES, PilotObservation, PILOT_NUMBERS, QUALITY_OUTCOMES
from reports import comparison_row, hours_range, observed_hours


def render_effort_assumptions(assessment: dict):
    st.markdown("### Preliminary readiness and effort savings")
    st.caption("User-supplied scenarios, not promised ROI. Discovery free text is never converted into numeric estimates.")
    assumptions = assessment.get("effort_assumptions") or EffortAssumptions().to_dict()
    estimate = estimate_opportunity(assessment)
    st.write(f"**Readiness:** {estimate['readiness']}")
    left, right = st.columns(2)
    left.metric("Net person-hours saved per week", hours_range(estimate["net_hours_per_week"]))
    right.metric("One-time implementation effort", hours_range(estimate["implementation_hours"]))
    st.caption(estimate["caveat"])
    if estimate["missing_inputs"]:
        st.info("Missing or unconfirmed inputs: " + "; ".join(estimate["missing_inputs"]))
    if estimate["input_errors"]:
        st.error("Invalid inputs: " + "; ".join(estimate["input_errors"]))
    with st.expander("Calculation and confirmed assumptions"):
        st.write(estimate["method"])
        st.write("Gross weekly effort reduction: " + hours_range(estimate["gross_hours_per_week"]))
        st.write(f"Assumptions last confirmed: {assumptions.get('confirmed_at') or 'Not confirmed'}")
        st.json(assumptions)
    with st.expander("Edit readiness and effort assumptions"):
        st.write("Use person-hours summed across the people in your baseline, for one typical week. "
                 "Keep all inputs within the same scope; no automatic expansion to the intended rollout.")
        st.caption("Leave unknown numbers blank. Zero is a real assumption, not an unknown value. "
                   "A partial draft can be saved; any edit requires fresh confirmation before an estimate is shown.")
        st.write(f"Discovery effort description: {assessment.get('discovery', {}).get('time_spent') or 'Not provided'}")
        with st.form(f"effort_{assessment['id']}"):
            scope = st.text_area("Baseline scope and evidence",
                                 value=assumptions.get("scope", ""),
                                 help="Who and what is included? State how effort was measured or estimated.")
            ranges = {}
            for key, (label, maximum) in EFFORT_RANGES.items():
                st.write(label)
                low, high = st.columns(2)
                current = assumptions.get(key) or [None, None]
                ranges[key] = [
                    low.number_input(f"{label} — lower", min_value=0.0, max_value=maximum,
                                     value=float(current[0]) if current[0] is not None else None,
                                     key=f"{assessment['id']}_{key}_low"),
                    high.number_input(f"{label} — upper", min_value=0.0, max_value=maximum,
                                      value=float(current[1]) if current[1] is not None else None,
                                      key=f"{assessment['id']}_{key}_high"),
                ]
            st.caption("Reduction is the fraction of baseline effort avoided on work using the solution. "
                       "Adoption is the fraction of baseline work expected to use it, not a headcount multiplier. "
                       "Review includes additional verification, exception handling, and maintenance after adoption. "
                       "Implementation includes setup, training, testing, and approval effort.")
            notes = st.text_area("Implementation assumptions and dependencies",
                                 value=assumptions.get("implementation_notes", ""),
                                 help="Describe setup, training, permissions, dependencies, and exclusions.")
            st.write("Pilot readiness — report what is known, not what is hoped for")
            readiness = {
                key: st.selectbox(label, READINESS_STATES,
                                  index=READINESS_STATES.index(
                                      assumptions.get("readiness", {}).get(key, "Not confirmed")),
                                  key=f"{assessment['id']}_{key}")
                for key, label in READINESS_CHECKS.items()
            }
            confirmed = st.checkbox(
                "I confirm the submitted assumptions for this scope; they are preliminary, not validated savings.",
                value=False,
                key=f"{assessment['id']}_effort_confirm_{assumptions.get('confirmed_at') or 'draft'}",
            )
            if st.form_submit_button("Save assumptions", type="primary"):
                try:
                    update_effort_assumptions(assessment["id"], {
                        **ranges, "scope": scope, "implementation_notes": notes,
                        "readiness": readiness, "confirmed": confirmed,
                    })
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.session_state.assessment = get_assessment(assessment["id"])
                    st.rerun()


def render_pilot_observation(assessment: dict):
    st.markdown("### Pilot observations versus preliminary scenario")
    pilot = assessment.get("pilot_observation") or PilotObservation().to_dict()
    result = evaluate_pilot(assessment)
    st.write(f"**Observed outcome:** {result['status']}")
    left, right = st.columns(2)
    left.metric("Observed total weekly effort", observed_hours(result["net_effort_hours_per_week"]))
    right.metric("Observed net weekly savings", observed_hours(result["net_savings_hours_per_week"]))
    st.write("Saved preliminary savings range: " + hours_range(result["scenario_net_hours_per_week"]))
    st.write(result["comparison"])
    st.caption(result["method"])
    st.write(f"Quality outcome: {result['quality_outcome']}")
    if result["quality_outcome"] in ("Worse", "Mixed", "Not measured"):
        st.warning("Time savings alone do not establish a successful pilot; review the quality evidence.")
    st.caption(result["caveat"])
    if assessment.get("pilot_observation"):
        if result["missing_inputs"]:
            st.info("Missing or unconfirmed pilot inputs: " + "; ".join(result["missing_inputs"]))
        if result["input_errors"]:
            st.error("; ".join(result["input_errors"]))
        with st.expander("Recorded pilot evidence and saved scenario"):
            st.json(pilot)
    with st.expander("Record or edit pilot observations"):
        st.write("Use weekly averages for the same people, tasks and workload. Include effort on "
                 "work not using the solution. Do not count review or rework twice.")
        st.caption("Blank means unknown; zero is valid. Drafts can be saved. "
                   "The first save captures the current preliminary assumptions separately; "
                   "later estimate or pilot edits do not replace that saved scenario.")
        scenario = pilot.get("scenario_assumptions", assessment.get("effort_assumptions") or {})
        st.write("Scenario scope: " + (scenario.get("scope") or "Not provided"))
        with st.form(f"pilot_{assessment['id']}"):
            values = {}
            for key, label in (
                ("scope", "Observed scope: people, tasks and workload"),
                ("observation_period", "Observation period: baseline and pilot dates / weeks"),
                ("measurement_notes", "Measurement method and evidence"),
            ):
                values[key] = st.text_area(label, value=pilot.get(key, ""),
                                          key=f"{assessment['id']}_pilot_{key}")
            values["same_scope"] = st.checkbox(
                "Baseline and pilot cover the saved scenario's same people, tasks and comparable weekly workload.",
                value=pilot.get("same_scope", False), key=f"{assessment['id']}_pilot_same_scope")
            for key, (label, maximum) in PILOT_NUMBERS.items():
                current = pilot.get(key)
                values[key] = st.number_input(
                    label, min_value=0.0, max_value=maximum,
                    value=float(current) if current is not None else None,
                    key=f"{assessment['id']}_pilot_{key}")
            values["quality_outcome"] = st.selectbox(
                "Observed quality outcome", QUALITY_OUTCOMES,
                index=QUALITY_OUTCOMES.index(pilot.get("quality_outcome", "Not measured")),
                key=f"{assessment['id']}_pilot_quality_outcome")
            values["quality_notes"] = st.text_area(
                "Quality evidence: baseline versus pilot errors, exceptions or acceptance; note if not measured",
                value=pilot.get("quality_notes", ""), key=f"{assessment['id']}_pilot_quality_notes")
            values["confirmed"] = st.checkbox(
                "I confirm these are recorded observations, including any zero savings or increased effort.",
                value=False,
                key=f"{assessment['id']}_pilot_confirm_{pilot.get('recorded_at') or 'draft'}")
            if st.form_submit_button("Save pilot observations", type="primary"):
                try:
                    update_pilot_observation(assessment["id"], values)
                except (ValueError, sqlite3.Error) as error:
                    st.error("Pilot observations were not saved. " + str(error))
                else:
                    st.session_state.assessment = get_assessment(assessment["id"])
                    st.rerun()


def render_comparison(assessments: list[dict]):
    st.markdown("### Compare readiness and effort savings")
    st.caption("Scenarios are preliminary; pilot observations are shown separately, not guaranteed ROI. Missing assumptions are shown, not treated as zero. "
               "Different baseline scopes are not directly comparable; estimates may overlap and must not be summed.")
    options = {item["id"]: item for item in assessments}
    selected = st.multiselect(
        "Choose opportunities to compare",
        list(options),
        default=list(options)[:3],
        format_func=lambda key: f"#{key} · {options[key]['title']}"
        + (" (fictional example)" if options[key].get("is_example") else ""),
        key="compare_opportunities",
    )
    if not selected:
        st.info("Choose at least one opportunity. Reopen an assessment below to enter or edit assumptions.")
        return
    chosen = [options[key] for key in selected]
    st.dataframe(pd.DataFrame([comparison_row(item) for item in chosen]),
                 hide_index=True, use_container_width=True)
    st.caption("Reopen an assessment below to enter, revise, or confirm its assumptions.")
    for item in chosen:
        estimate = estimate_opportunity(item)
        with st.expander(f"#{item['id']} · Readiness evidence and method"):
            for check in estimate["readiness_checks"]:
                st.write(f"{check['check']}: {check['status']}")
            st.write(estimate["method"])
            st.write(estimate["caveat"])
