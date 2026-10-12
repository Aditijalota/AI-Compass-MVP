"""Offline checks for transparent scenarios, persistence, exports, and Streamlit UI."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import database
from classification import classify, estimate_opportunity
from models import READINESS_CHECKS
from reports import assessment_as_json, assessment_as_text, comparison_row
from streamlit.testing.v1 import AppTest


def valid_assumptions():
    return {
        "baseline_hours": [10.0, 20.0],
        "reduction_percent": [20.0, 50.0],
        "adoption_percent": [50.0, 80.0],
        "review_hours": [1.0, 2.0],
        "implementation_hours": [12.0, 30.0],
        "scope": "One fictional team; weekly sampled person-hours",
        "implementation_notes": "Approved tools, setup and training; no external connection",
        "readiness": dict.fromkeys(READINESS_CHECKS, "Confirmed"),
        "confirmed": True,
    }


class EstimateTests(unittest.TestCase):
    def estimate(self, assumptions):
        return estimate_opportunity({"effort_assumptions": assumptions})

    def test_interval_math_includes_overhead_and_negative_savings(self):
        result = self.estimate(valid_assumptions())
        self.assertEqual(result["gross_hours_per_week"], [1.0, 8.0])
        self.assertEqual(result["net_hours_per_week"], [-1.0, 7.0])
        self.assertEqual(result["implementation_hours"], [12.0, 30.0])
        self.assertEqual(result["readiness"], "Pilot prerequisites reported confirmed")
        self.assertIn("not measured results", result["caveat"])

    def test_rollout_and_free_text_never_inflate_or_supply_estimates(self):
        item = classify(database.EXAMPLES[1], "2026-10-12").to_dict()
        self.assertIsNone(estimate_opportunity(item)["net_hours_per_week"])
        self.assertIn("Baseline person-hours per week", estimate_opportunity(item)["missing_inputs"])
        item["effort_assumptions"] = valid_assumptions()
        self.assertEqual(estimate_opportunity(item)["net_hours_per_week"], [-1, 7])
        item["rollout_scale"] = "Global"
        self.assertEqual(estimate_opportunity(item)["net_hours_per_week"], [-1, 7])

    def test_missing_and_unconfirmed_inputs_are_not_zero(self):
        for key in ["baseline_hours", "review_hours", "implementation_hours", "scope",
                    "implementation_notes", "confirmed"]:
            assumptions = valid_assumptions()
            assumptions.pop(key)
            result = self.estimate(assumptions)
            self.assertIsNone(result["net_hours_per_week"], key)
            self.assertTrue(result["missing_inputs"], key)
        self.assertIsNone(estimate_opportunity({})["net_hours_per_week"])

    def test_zero_and_equal_endpoints_are_valid(self):
        assumptions = valid_assumptions()
        for key in ["baseline_hours", "review_hours", "implementation_hours",
                    "reduction_percent", "adoption_percent"]:
            assumptions[key] = [0.0, 0.0]
        result = self.estimate(assumptions)
        self.assertEqual(result["net_hours_per_week"], [0, 0])
        self.assertFalse(result["input_errors"])

    def test_invalid_ranges_are_rejected_without_a_result(self):
        for key, values in [
            ("baseline_hours", [20, 10]), ("review_hours", [-1, 3]),
            ("reduction_percent", [10, 101]), ("adoption_percent", [True, 50]),
            ("baseline_hours", [float("nan"), 10]),
            ("baseline_hours", [0, float("inf")]),
            ("baseline_hours", ["10", 20]), ("baseline_hours", [10]),
        ]:
            assumptions = valid_assumptions()
            assumptions[key] = values
            result = self.estimate(assumptions)
            self.assertTrue(result["input_errors"], values)
            self.assertIsNone(result["net_hours_per_week"])

    def test_readiness_is_evidence_not_a_score_or_roi_gate(self):
        assumptions = valid_assumptions()
        assumptions["readiness"]["owner"] = "Needs work"
        self.assertEqual(self.estimate(assumptions)["readiness"], "Needs preparation")
        assumptions["readiness"] = {}
        result = self.estimate(assumptions)
        self.assertEqual(result["readiness"], "Readiness unconfirmed")
        self.assertEqual(len(result["missing_inputs"]), 4)
        self.assertEqual(result["net_hours_per_week"], [-1, 7])


class PersistenceAndUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp.name) / "test.db")
        self.db_patch.start()
        database.initialize_database()

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def test_update_preserves_example_and_original_assessment_and_exports(self):
        original = database.list_assessments()[0]
        count = len(database.list_assessments())
        database.update_effort_assumptions(original["id"], valid_assumptions())
        updated = database.get_assessment(original["id"])
        for key in ["discovery", "is_example", "created_at", "solution_pattern", "id"]:
            self.assertEqual(original[key], updated[key])
        self.assertEqual(count, len(database.list_assessments()))
        self.assertTrue(updated["effort_assumptions"]["confirmed_at"])
        exported = json.loads(assessment_as_json(updated))
        self.assertEqual(exported["preliminary_estimate"]["net_hours_per_week"], [-1, 7])
        text = assessment_as_text(updated)
        for content in ["-1.00 to 7.00", "one-time", "not measured results", "sampled"]:
            self.assertIn(content, text)
        self.assertEqual(comparison_row(updated)["Type"], "Fictional example")
        bad = valid_assumptions()
        bad["adoption_percent"] = [101, 102]
        with self.assertRaises(ValueError):
            database.update_effort_assumptions(original["id"], bad)
        self.assertEqual(database.get_assessment(original["id"]), updated)
        with self.assertRaises(ValueError):
            database.update_effort_assumptions(999, valid_assumptions())

    def test_legacy_assessment_exports_without_new_fields(self):
        original = database.list_assessments()[0]
        original.pop("effort_assumptions", None)
        self.assertIn("Not estimated", assessment_as_text(original))
        self.assertIsNone(json.loads(assessment_as_json(original))["preliminary_estimate"]["net_hours_per_week"])
        self.assertIn("Missing", comparison_row(original)["Net weekly effort savings"].replace("missing", "Missing"))

    def app(self):
        return AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=15).run()

    def button(self, app, label):
        return next(button for button in app.button if button.label == label)

    def test_edit_confirm_compare_reopen_and_reset_confirmation(self):
        app = self.app()
        app.radio(key="navigation").set_value("Opportunity Dashboard").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.multiselect[0].value), 3)
        self.button(app, "Reopen assessment").click().run()
        self.assertFalse(app.exception)
        assessment_id = app.session_state.assessment_id
        assumptions = valid_assumptions()
        for key in ["baseline_hours", "reduction_percent", "adoption_percent",
                    "review_hours", "implementation_hours"]:
            for index, suffix in enumerate(["low", "high"]):
                app.number_input(key=f"{assessment_id}_{key}_{suffix}").set_value(assumptions[key][index])
        for area in app.text_area:
            if area.label == "Baseline scope and evidence":
                area.set_value(assumptions["scope"])
            elif area.label == "Implementation assumptions and dependencies":
                area.set_value(assumptions["implementation_notes"])
        for key in READINESS_CHECKS:
            app.selectbox(key=f"{assessment_id}_{key}").set_value("Confirmed")
        confirm = next(box for box in app.checkbox if box.label.startswith("I confirm the submitted"))
        confirm.check()
        self.button(app, "Save assumptions").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(estimate_opportunity(database.get_assessment(assessment_id))["net_hours_per_week"], [-1, 7])
        confirm = next(box for box in app.checkbox if box.label.startswith("I confirm the submitted"))
        self.assertFalse(confirm.value)
        self.button(app, "← Return to dashboard").click().run()
        self.assertFalse(app.exception)
        compared = app.dataframe[-1].value
        self.assertIn("-1.00 to 7.00 person-hours", compared["Net weekly effort savings"].tolist())
        self.button(app, "Reopen assessment").click().run()
        self.assertEqual(app.number_input(key=f"{assessment_id}_baseline_hours_low").value, 10)
        # Changing values without confirming again removes the result, not the record.
        app.number_input(key=f"{assessment_id}_baseline_hours_low").set_value(11)
        self.button(app, "Save assumptions").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(estimate_opportunity(database.get_assessment(assessment_id))["net_hours_per_week"])
        fresh = self.app()
        fresh.radio(key="navigation").set_value("Opportunity Dashboard").run()
        self.button(fresh, "Reopen assessment").click().run()
        self.assertEqual(fresh.number_input(key=f"{assessment_id}_baseline_hours_low").value, 11)

    def test_partial_draft_and_invalid_input_ui(self):
        app = self.app()
        app.radio(key="navigation").set_value("Opportunity Dashboard").run()
        self.button(app, "Reopen assessment").click().run()
        assessment_id = app.session_state.assessment_id
        app.number_input(key=f"{assessment_id}_baseline_hours_low").set_value(10)
        self.button(app, "Save assumptions").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(database.get_assessment(assessment_id)["effort_assumptions"]["baseline_hours"], [10, None])
        before = copy.deepcopy(database.get_assessment(assessment_id))
        app.number_input(key=f"{assessment_id}_baseline_hours_high").set_value(5)
        self.button(app, "Save assumptions").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("lower value cannot exceed" in error.value for error in app.error))
        self.assertEqual(database.get_assessment(assessment_id), before)
        self.button(app, "← Return to dashboard").click().run()
        app.multiselect[0].set_value([]).run()
        self.assertFalse(app.exception)
        app.text_input(key="dashboard_search").set_value("does not match anything").run()
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
