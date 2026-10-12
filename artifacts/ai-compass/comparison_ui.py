"""Streamlit controls for explicit effort assumptions and opportunity comparison."""

import pandas as pd
import streamlit as st

from classification import estimate_opportunity
from database import get_assessment, update_effort_assumptions
from models import EffortAssumptions, EFFORT_RANGES, READINESS_CHECKS, READINESS_STATES
from reports import comparison_row, hours_range


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


def render_comparison(assessments: list[dict]):
    st.markdown("### Compare readiness and effort savings")
    st.caption("All results are preliminary. Missing assumptions are shown, not treated as zero. "
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
