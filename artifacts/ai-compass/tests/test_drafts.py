"""Draft persistence and UI checks without billed model requests."""

from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import database
import discovery
from draft_state import empty_draft, restore_state
from streamlit.testing.v1 import AppTest


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp.name) / "prototype.db")
        self.db_patch.start()
        database.initialize_database()

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def button(self, app, label):
        return next(button for button in app.button if button.label == label)

    def app(self):
        app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=15).run()
        self.assertFalse(app.exception)
        return app

    def start(self, app):
        app.button(key="path_problem").click().run()
        app.text_area[0].set_value("Fictional checks")
        self.button(app, "Continue to discovery").click().run()
        self.assertFalse(app.exception)

    def test_crud_allowlist_progress_and_existing_assessments(self):
        draft = {**empty_draft(), "intake_path": "problem", "role": "Team lead",
                 "ai_authorized": True, "use_ai": True, "secret": "must not persist"}
        draft_id = database.save_discovery_draft(draft, 3, {0, 1, 2})
        stored = database.get_discovery_draft(draft_id)
        self.assertEqual(stored["saved_exchanges"], [0, 1, 2])
        self.assertEqual(stored["step"], 3)
        self.assertFalse({"ai_authorized", "use_ai", "secret"} & stored["draft"].keys())
        self.assertNotIn("ai_authorized", stored)
        draft["role"] = "Updated role"
        self.assertEqual(database.save_discovery_draft(draft, 5, range(6), draft_id=draft_id), draft_id)
        self.assertEqual(len(database.list_discovery_drafts()), 1)
        self.assertEqual(database.get_discovery_draft(draft_id)["draft"]["role"], "Updated role")
        database.discard_discovery_draft(draft_id)
        self.assertEqual(database.list_discovery_drafts(), [])
        with self.assertRaises(ValueError):
            database.save_discovery_draft(draft, 0, [], draft_id=draft_id)
        self.assertEqual(len(database.list_assessments()), 3)

    def test_restore_clears_stale_fields_and_every_ai_permission(self):
        draft_id = database.save_discovery_draft(
            {**empty_draft(), "intake_path": "explore", "department": "HR"}, 5, range(6),
        )
        state = {"step_0_department": "Finance", "step_1_activities": "Old",
                 "ai_discovery": True, "ai_authorized": True, "use_ai": True,
                 "ai_enrichment_authorized": True, "discovery_prompts": {"old": "AI"}}
        restore_state(state, database.get_discovery_draft(draft_id))
        self.assertFalse(any(key.startswith("step_") for key in state))
        for key in ("ai_discovery", "ai_authorized", "use_ai", "ai_enrichment_authorized"):
            self.assertFalse(state[key])
        self.assertEqual(state["saved_exchanges"], set(range(6)))
        self.assertEqual(state["discovery_prompts"], {})

    def test_save_current_fields_new_session_resume_and_fresh_consent(self):
        with patch.object(discovery, "_select_with_ai", return_value=next(iter(discovery.FOLLOW_UPS[1]))) as model, patch.object(
            discovery, "ai_available", return_value=True
        ), patch("llm_demo.assessment_insight") as insight:
            app = self.app()
            self.start(app)
            self.assertTrue(self.button(app, "Save draft for later").disabled)
            app.checkbox(key="draft_storage_authorized").check().run()
            app.selectbox(key="step_0_department").set_value("Operations")
            app.text_input(key="step_0_role").set_value("Fictional coordinator")
            app.selectbox(key="step_0_problem_scale").set_value("Organization")
            app.text_area(key="step_0_desired_outcome").set_value("Faster checks")
            self.button(app, "Save exchange and continue").click().run()
            app.text_area(key="step_1_activities").set_value("Fictional current unfinished work")
            app.text_area(key="step_1_frequency").set_value("Weekly")
            self.button(app, "Save draft for later").click().run()
            self.assertFalse(app.exception)
            saved = database.list_discovery_drafts()[0]
            payload = database.get_discovery_draft(saved["id"])
            self.assertEqual(payload["step"], 1)
            self.assertEqual(payload["saved_exchanges"], [0])
            self.assertEqual(payload["draft"]["activities"], "Fictional current unfinished work")

            # A fresh AppTest instance represents a lost Streamlit/browser session.
            resumed = self.app()
            resumed.toggle(key="use_ai").set_value(True).run()
            resumed.checkbox(key="ai_enrichment_authorized").check().run()
            self.button(resumed, "Resume draft").click().run()
            self.assertFalse(resumed.exception)
            self.assertEqual(resumed.session_state.page, "Discovery Studio")
            self.assertEqual(resumed.session_state.step, 1)
            self.assertEqual(resumed.session_state.saved_exchanges, {0})
            self.assertEqual(resumed.text_area(key="step_1_activities").value, "Fictional current unfinished work")
            self.assertEqual(resumed.session_state.draft["department"], "Operations")
            self.assertEqual(resumed.session_state.draft["role"], "Fictional coordinator")
            self.assertEqual(resumed.session_state.draft["problem_scale"], "Organization")
            self.assertFalse(resumed.toggle(key="use_ai").value)
            self.assertFalse(resumed.checkbox(key="ai_enrichment_authorized").value)
            model.assert_not_called()
            self.button(resumed, "Generate preliminary assessment").click().run()
            insight.assert_not_called()
            self.button(resumed, "Resume draft").click().run()
            resumed.toggle(key="ai_discovery").set_value(True).run()
            model.assert_not_called()
            resumed.checkbox(key="ai_authorized").check().run()
            model.assert_called_once()
            # Resume in the same session resets both discovery widgets and cache.
            self.button(resumed, "Resume draft").click().run()
            self.assertFalse(resumed.exception)
            self.assertFalse(resumed.toggle(key="ai_discovery").value)
            self.assertFalse(resumed.checkbox(key="ai_authorized").value)
            self.assertEqual(model.call_count, 1)
            resumed.checkbox(key="draft_storage_authorized").check().run()
            resumed.text_area(key="step_1_activities").set_value("Updated fictional work")
            self.button(resumed, "Save draft for later").click().run()
            self.assertEqual(len(database.list_discovery_drafts()), 1)
            self.assertEqual(database.get_discovery_draft(saved["id"])["draft"]["activities"], "Updated fictional work")

    def test_discard_requires_confirmation_and_does_not_delete_assessments(self):
        draft_id = database.save_discovery_draft({**empty_draft(), "intake_path": "problem"}, 5, range(6))
        app = self.app()
        self.button(app, "Resume draft").click().run()
        self.assertTrue(any("All six exchanges" in message.value for message in app.success))
        self.assertTrue(self.button(app, "Discard saved draft").disabled)
        app.checkbox(key="discard_draft_confirm").check().run()
        self.button(app, "Discard saved draft").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(database.list_discovery_drafts(), [])
        self.assertIsNone(app.session_state.active_draft_id)
        self.assertEqual(app.session_state.saved_exchanges, set(range(6)))
        self.assertEqual(len(database.list_assessments()), 3)
        with self.assertRaises(ValueError):
            database.get_discovery_draft(draft_id)

    def test_save_failure_is_visible_and_does_not_report_success(self):
        app = self.app()
        self.start(app)
        app.checkbox(key="draft_storage_authorized").check().run()
        with patch.object(database, "save_discovery_draft", side_effect=sqlite3.OperationalError("database unavailable")):
            self.button(app, "Save draft for later").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Draft was not saved" in message.value for message in app.error))
        self.assertIsNone(app.session_state.active_draft_id)
        self.assertEqual(database.list_discovery_drafts(), [])


if __name__ == "__main__":
    unittest.main()
