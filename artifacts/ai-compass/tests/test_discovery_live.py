"""Explicitly opted-in smoke test: one real managed AI request through the UI."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import database
import discovery
from streamlit.testing.v1 import AppTest


@unittest.skipUnless(
    os.environ.get("RUN_DISCOVERY_LIVE_SMOKE") == "1",
    "Live AI smoke is opt-in and billed to Replit credits.",
)
class LiveDiscoverySmokeTests(unittest.TestCase):
    def test_one_live_selection_consent_cache_and_failure_fallback(self):
        self.assertTrue(discovery.ai_available(), "Managed OpenAI configuration is required.")
        with tempfile.TemporaryDirectory() as directory, patch.object(
            database, "DB_PATH", Path(directory) / "smoke.db"
        ), patch.object(
            discovery, "_select_with_ai", wraps=discovery._select_with_ai
        ) as model:
            app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=30).run()

            def button(label):
                return next(item for item in app.button if item.label == label)

            def healthy():
                self.assertFalse(app.exception, "Discovery Studio must render without errors.")

            app.button(key="path_problem").click().run()
            app.text_area[0].set_value("Fictional team waits for approvals of sample purchase orders.")
            button("Continue to discovery").click().run()
            healthy()
            self.assertEqual(app.session_state.page, "Discovery Studio")
            self.assertFalse(app.session_state.ai_discovery)
            self.assertFalse(app.session_state.ai_authorized)
            model.assert_not_called()

            app.toggle(key="ai_discovery").set_value(True).run()
            model.assert_not_called()
            self.assertTrue(any("AI has not been used" in item.value for item in app.warning))
            app.checkbox(key="ai_authorized").check().run()
            healthy()
            self.assertEqual(model.call_count, 1)
            self.assertTrue(any(
                f"AI-selected follow-up · OpenAI {discovery.AI_MODEL} via Replit AI Integrations"
                == item.value for item in app.caption
            ), "The live provider must return a valid selection, not guided fallback.")
            key = discovery.prompt_cache_key(0, app.session_state.draft, True, True)
            selected = app.session_state.discovery_prompts[key]
            self.assertEqual(selected.source, "ai")
            self.assertTrue(any(selected.text.startswith(text) for text in discovery.FOLLOW_UPS[0].values()))

            app.run()
            app.toggle(key="ai_discovery").set_value(False).run()
            self.assertTrue(any(
                "no model used for this question" in item.value for item in app.caption
            ))
            self.assertIn("Fictional team", app.session_state.draft["business_problem"])
            app.toggle(key="ai_discovery").set_value(True).run()
            self.assertEqual(model.call_count, 1, "Reruns and toggles must reuse the session selection.")
            self.assertEqual(app.session_state.discovery_prompts[key], selected)

            # Force a failure on the next exchange without another billed request.
            with patch.object(discovery, "_select_with_ai", side_effect=TimeoutError("private details")) as failed:
                button("Save exchange and continue").click().run()
                healthy()
                failed.assert_called_once()
                self.assertTrue(any(
                    "AI question selection failed" in item.value for item in app.warning
                ))
                self.assertTrue(any(
                    "no model used for this question" in item.value for item in app.caption
                ))
                self.assertFalse(any("private details" in item.value for item in app.warning))
                app.run()
                failed.assert_called_once()

            app.radio(key="navigation").set_value("Welcome").run()
            app.text_area[0].set_value("Another fictional process")
            button("Continue to discovery").click().run()
            healthy()
            self.assertFalse(app.session_state.ai_discovery)
            self.assertFalse(app.session_state.ai_authorized)
            self.assertEqual(model.call_count, 1)


if __name__ == "__main__":
    unittest.main()
