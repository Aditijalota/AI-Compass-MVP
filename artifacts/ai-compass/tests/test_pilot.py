"""Offline pilot arithmetic, snapshot persistence, exports and UI checks."""

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
from classification import evaluate_pilot
from models import PilotObservation
from reports import assessment_as_json, assessment_as_text, comparison_row
from test_estimates import valid_assumptions
from streamlit.testing.v1 import AppTest


def observation():
    return {
        **PilotObservation().to_dict(),
        "scope": "One fictional team; same invoice workload",
        "observation_period": "Baseline: September, pilot: October; four weeks each",
        "measurement_notes": "Weekly time logs for every participant; equal ticket volume",
        "baseline_hours": 10.0, "adoption_percent": 50.0,
        "work_hours": 6.0, "review_hours": 2.0,
        "same_scope": True, "quality_outcome": "Unchanged",
        "quality_notes": "Same sample acceptance rate and errors",
        "confirmed": True,
    }


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp.name) / "test.db")
        self.db_patch.start()
        database.initialize_database()
        self.item = database.list_assessments()[0]
        self.id = self.item["id"]
        database.update_effort_assumptions(self.id, valid_assumptions())

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def result(self, pilot=None):
        database.update_pilot_observation(self.id, pilot or observation())
        return evaluate_pilot(database.get_assessment(self.id))

    def test_arithmetic_quality_zero_and_negative_savings(self):
        pilot = observation()
        for work, expected, status in [(6, 2, "Time saved"), (8, 0, "No time saved"),
                                       (9, -1, "Additional effort")]:
            pilot["work_hours"] = work
            result = self.result(pilot)
            self.assertEqual(result["net_effort_hours_per_week"], work + 2)
            self.assertEqual(result["net_savings_hours_per_week"], expected)
            self.assertEqual(result["status"], status)
        pilot.update(baseline_hours=0, work_hours=0, review_hours=0, adoption_percent=0,
                     quality_outcome="Worse")
        result = self.result(pilot)
        self.assertEqual(result["net_savings_hours_per_week"], 0)
        self.assertEqual(result["quality_outcome"], "Worse")

    def test_comparison_boundaries_missing_and_mismatched_scope(self):
        for work, position in [(10, "Below"), (6, "Within"), (0, "Above"), (9, "Within")]:
            pilot = observation()
            pilot["work_hours"] = work
            self.assertTrue(self.result(pilot)["comparison"].startswith(position))
        pilot["same_scope"] = False
        self.assertIn("Not comparable", self.result(pilot)["comparison"])
        legacy = evaluate_pilot({})
        self.assertEqual(legacy["status"], "Not recorded")
        pilot["scenario_assumptions"] = {}
        pilot["same_scope"] = True
        self.assertIn("missing or unconfirmed", evaluate_pilot({"pilot_observation": pilot})["comparison"])

    def test_unknown_unconfirmed_and_invalid_values(self):
        for key in ("baseline_hours", "adoption_percent", "work_hours", "review_hours",
                    "measurement_notes", "quality_notes", "observation_period", "confirmed"):
            pilot = observation()
            pilot.pop(key)
            self.assertIsNone(self.result(pilot)["net_savings_hours_per_week"], key)
        before = database.get_assessment(self.id)
        for key, value in [("adoption_percent", 101), ("review_hours", -1),
                           ("work_hours", float("inf")), ("baseline_hours", float("nan")),
                           ("work_hours", True), ("same_scope", "yes"),
                           ("quality_outcome", "Great"), ("scope", 123)]:
            pilot = observation()
            pilot[key] = value
            with self.assertRaises(ValueError):
                database.update_pilot_observation(self.id, pilot)
            self.assertEqual(database.get_assessment(self.id), before)
        pilot = observation()
        pilot.update(work_hours=1e308, review_hours=1e308)
        self.assertIsNone(self.result(pilot)["net_savings_hours_per_week"])

    def test_scenario_is_preserved_through_estimate_and_pilot_edits_and_exports(self):
        before = database.get_assessment(self.id)
        self.result()
        saved = database.get_assessment(self.id)
        self.assertEqual(saved["effort_assumptions"], before["effort_assumptions"])
        for key in ("discovery", "is_example", "created_at", "solution_pattern"):
            self.assertEqual(saved[key], before[key])
        scenario = copy.deepcopy(saved["pilot_observation"]["scenario_assumptions"])
        newer = valid_assumptions()
        newer["baseline_hours"] = [100, 200]
        database.update_effort_assumptions(self.id, newer)
        pilot = observation()
        pilot["scenario_assumptions"] = newer  # client cannot replace the snapshot
        pilot["work_hours"] = 9
        self.result(pilot)
        reopened = database.get_assessment(self.id)
        self.assertEqual(reopened["pilot_observation"]["scenario_assumptions"], scenario)
        self.assertEqual(evaluate_pilot(reopened)["scenario_net_hours_per_week"], [-1, 7])
        data = json.loads(assessment_as_json(reopened))
        self.assertEqual(data["pilot_result"]["net_savings_hours_per_week"], -1)
        self.assertIn("Additional effort", assessment_as_text(reopened))
        self.assertEqual(comparison_row(reopened)["Observed net weekly savings"], "-1.00 person-hours")
        with self.assertRaises(ValueError):
            database.update_pilot_observation(999999, pilot)

    def test_ui_save_reopen_edit_draft_and_dashboard(self):
        def button(app, label):
            return next(item for item in app.button if item.label == label)

        def reopen():
            app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=15).run()
            app.radio(key="navigation").set_value("Opportunity Dashboard").run()
            button(app, "Reopen assessment").click().run()
            self.assertFalse(app.exception)
            return app

        app = reopen()
        self.assertEqual(app.session_state.assessment_id, self.id)
        pilot = observation()
        pilot["work_hours"] = 9
        for key in ("scope", "observation_period", "measurement_notes", "quality_notes"):
            app.text_area(key=f"{self.id}_pilot_{key}").set_value(pilot[key])
        for key in ("baseline_hours", "adoption_percent", "work_hours", "review_hours"):
            app.number_input(key=f"{self.id}_pilot_{key}").set_value(pilot[key])
        app.checkbox(key=f"{self.id}_pilot_same_scope").check()
        app.selectbox(key=f"{self.id}_pilot_quality_outcome").set_value("Unchanged")
        next(box for box in app.checkbox if box.label.startswith("I confirm these")).check()
        button(app, "Save pilot observations").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(evaluate_pilot(database.get_assessment(self.id))["status"], "Additional effort")
        self.assertFalse(next(box for box in app.checkbox if box.label.startswith("I confirm these")).value)
        button(app, "← Return to dashboard").click().run()
        self.assertIn("Additional effort", app.dataframe[-1].value["Pilot outcome"].tolist())
        fresh = reopen()
        self.assertEqual(fresh.number_input(key=f"{self.id}_pilot_work_hours").value, 9)
        fresh.number_input(key=f"{self.id}_pilot_work_hours").set_value(8)
        button(fresh, "Save pilot observations").click().run()
        self.assertFalse(fresh.exception)
        self.assertIsNone(evaluate_pilot(database.get_assessment(self.id))["net_savings_hours_per_week"])


if __name__ == "__main__":
    unittest.main()
