"""Offline checks for bounded prompts, opt-in, and the six-exchange UI."""

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import database
import discovery
from classification import classify
from streamlit.testing.v1 import AppTest


class PromptTests(unittest.TestCase):
    def test_all_six_exchanges_work_without_configuration(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(discovery, "_select_with_ai") as model:
            for index, question in enumerate(discovery.QUESTIONS):
                prompt = discovery.discovery_prompt(index, {"department": "Finance"})
                self.assertEqual(prompt.source, "guided")
                self.assertIn(question["prompt"], prompt.text)
            model.assert_not_called()

    def test_guided_question_adapts_to_previous_answers(self):
        pairs = [
            (0, {}, {"business_problem": "Slow approvals"}),
            (1, {"business_problem": "Manual copying"}, {"business_problem": "Approval delays"}),
            (2, {"activities": "Read emails"}, {"activities": "Check spreadsheet rows"}),
            (3, {"data_types": "PDF documents"}, {"data_types": "Incomplete rows"}),
            (4, {"rules": "Fixed checks"}, {"rules": "Checks", "exceptions": "Review missing rows"}),
            (5, {"business_impact": "Faster work"}, {"business_impact": "Faster reviews"}),
        ]
        for index, first, second in pairs:
            self.assertNotEqual(
                discovery.discovery_prompt(index, first).text,
                discovery.discovery_prompt(index, second).text,
            )

    def test_no_model_without_consent_or_configuration(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(discovery, "_select_with_ai") as model:
            for authorized in [False, True]:
                prompt = discovery.discovery_prompt(2, {}, use_ai=True, authorized=authorized)
                self.assertEqual(prompt.source, "guided")
                self.assertTrue(prompt.notice)
            model.assert_not_called()

    def test_context_is_bounded_and_excludes_current_and_future_fields(self):
        draft = {
            "department": "Finance", "activities": "x" * 2000,
            "business_problem": "Fictional delay", "data_types": "unsaved",
            "constraints": "future", "unknown": "not allowed",
        }
        context = discovery.prior_context(2, draft)
        self.assertEqual(len(context["activities"]), 600)
        self.assertFalse({"data_types", "constraints", "unknown"} & context.keys())
        key = discovery.prompt_cache_key(2, draft, False, False)
        self.assertEqual(key, discovery.prompt_cache_key(2, {**draft, "data_types": "changed"}, False, False))
        self.assertNotEqual(key, discovery.prompt_cache_key(2, {**draft, "activities": "new"}, False, False))

    def test_ai_sdk_request_and_selection_are_bounded(self):
        client = MagicMock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"question_id":"documents"}'))]
        )
        with patch.dict("os.environ", {
            "AI_INTEGRATIONS_OPENAI_BASE_URL": "https://example.invalid",
            "AI_INTEGRATIONS_OPENAI_API_KEY": "test-placeholder",
        }), patch("openai.OpenAI", return_value=client) as constructor:
            draft = {"activities": "Read fictional emails", "tools": "unsaved"}
            before = draft.copy()
            prompt = discovery.discovery_prompt(2, draft, use_ai=True, authorized=True)
            self.assertEqual(prompt.source, "ai")
            self.assertIn(discovery.FOLLOW_UPS[2]["documents"], prompt.text)
            self.assertEqual(draft, before)
            args = client.chat.completions.create.call_args.kwargs
            self.assertEqual(args["model"], discovery.AI_MODEL)
            payload = json.loads(args["messages"][1]["content"])
            self.assertNotIn("tools", payload["saved_answers"])
            self.assertEqual(payload["allowed_questions"], discovery.FOLLOW_UPS[2])
            self.assertNotIn("tools", args)
            self.assertEqual(constructor.call_args.kwargs["max_retries"], 0)
            client.close.assert_called_once()

    def test_invalid_or_failed_ai_selection_falls_back(self):
        invalid = [
            "not JSON", '{"question_id":"pilot"}',
            '{"question_id":"documents","recommendation":"AI"}',
            '{"question_id":["documents"]}', "[]" , "x" * 501,
        ]
        with patch.dict("os.environ", {
            "AI_INTEGRATIONS_OPENAI_BASE_URL": "https://example.invalid",
            "AI_INTEGRATIONS_OPENAI_API_KEY": "test-placeholder",
        }):
            for content in invalid:
                client = MagicMock()
                client.chat.completions.create.return_value = SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
                )
                with patch("openai.OpenAI", return_value=client):
                    prompt = discovery.discovery_prompt(2, {}, use_ai=True, authorized=True)
                    self.assertEqual(prompt.source, "guided")
                    self.assertIn("invalid response", prompt.notice)
            with patch.object(discovery, "_select_with_ai", side_effect=TimeoutError("sensitive provider details")):
                prompt = discovery.discovery_prompt(2, {}, use_ai=True, authorized=True)
                self.assertNotIn("sensitive provider details", prompt.notice)

    def test_ai_does_not_change_classifier(self):
        draft = database.EXAMPLES[0].copy()
        expected = classify(draft, "2026-10-12").to_dict()
        with patch.object(discovery, "ai_available", return_value=True), patch.object(
            discovery, "_select_with_ai", return_value="steps"
        ):
            discovery.discovery_prompt(1, draft, use_ai=True, authorized=True)
        self.assertEqual(expected, classify(draft, "2026-10-12").to_dict())


class DiscoveryUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp.name) / "assessments.db")
        self.db_patch.start()
        self.model_patch = patch.object(discovery, "_select_with_ai", side_effect=lambda index, context: next(iter(discovery.FOLLOW_UPS[index])))
        self.model = self.model_patch.start()
        self.available_patch = patch.object(discovery, "ai_available", return_value=True)
        self.available_patch.start()
        self.app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=15).run()

    def tearDown(self):
        self.available_patch.stop()
        self.model_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def button(self, label):
        return next(button for button in self.app.button if button.label == label)

    def start(self):
        self.app.button(key="path_problem").click().run()
        self.app.text_area[0].set_value("Fictional team waits for approvals")
        self.button("Continue to discovery").click().run()
        self.assertFalse(self.app.exception)

    def test_six_exchanges_back_edit_and_rules_based_assessment(self):
        self.start()
        for index in range(6):
            self.assertEqual(self.app.session_state.step, index)
            for area in self.app.text_area:
                area.set_value(f"Fictional exchange {index + 1}: repeated checks and review")
            self.button("Save final exchange" if index == 5 else "Save exchange and continue").click().run()
            self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.session_state.saved_exchanges), 6)
        self.button("← Previous exchange").click().run()
        self.app.text_area[0].set_value("About two hours weekly")
        self.button("Save exchange and continue").click().run()
        self.assertEqual(self.app.session_state.draft["time_spent"], "About two hours weekly")
        self.button("Generate preliminary assessment").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state.page, "Assessment")
        self.assertEqual(len(database.list_assessments()), 4)
        self.model.assert_not_called()

    def test_opt_in_cache_switch_off_and_new_discovery_reset(self):
        self.start()
        self.app.toggle(key="ai_discovery").set_value(True).run()
        self.model.assert_not_called()
        self.app.checkbox(key="ai_authorized").check().run()
        self.assertEqual(self.model.call_count, 1)
        self.app.run()
        self.assertEqual(self.model.call_count, 1)
        self.app.toggle(key="ai_discovery").set_value(False).run()
        self.assertEqual(self.model.call_count, 1)
        self.assertEqual(self.app.session_state.draft["business_problem"], "Fictional team waits for approvals")
        self.app.toggle(key="ai_discovery").set_value(True).run()
        self.assertEqual(self.model.call_count, 1)
        self.app.radio(key="navigation").set_value("Welcome").run()
        self.app.text_area[0].set_value("Another fictional process")
        self.button("Continue to discovery").click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.session_state.ai_discovery)
        self.assertFalse(self.app.session_state.ai_authorized)
        self.assertEqual(self.model.call_count, 1)

    def test_incoming_demo_prefills_work_for_all_three_paths(self):
        from demo_examples import DEMOS
        for path, example in DEMOS.items():
            self.app.button(key=f"load_demo_{path}").click().run()
            self.assertFalse(self.app.exception)
            self.assertEqual(self.app.session_state.demo_path, path)
            if path == "problem":
                self.assertEqual(self.app.text_area[0].value, example["business_problem"])
                self.button("Continue to discovery").click().run()
            else:
                label = "Show three opportunities" if path == "explore" else "Suggest starting points"
                self.button(label).click().run()
                self.assertEqual(len(self.app.session_state.suggestions), 3)
                self.app.button(key="choose_opportunity_0").click().run()
            self.assertFalse(self.app.exception)
            self.assertEqual(self.app.session_state.page, "Discovery Studio")
            outcome = next(area for area in self.app.text_area if area.label == "Desired outcome")
            self.assertEqual(outcome.value, example["desired_outcome"])
            self.assertFalse(self.app.session_state.ai_discovery)
        self.model.assert_not_called()

    def test_incoming_ai_enrichment_is_preserved_and_requires_consent(self):
        suggestions = [
            {"title": f"Fictional opportunity {index}", "description": "Review fictional reports.",
             "department": "Finance", "role": "", "ai_model": discovery.AI_MODEL}
            for index in range(3)
        ]
        insight = {"summary": "An explicitly labeled interpretation.",
                   "pilot_plan": ["Confirm scope", "Review outputs", "Measure accuracy"],
                   "model": discovery.AI_MODEL}
        with patch("llm_demo.opportunities", return_value=suggestions) as opportunities, patch(
            "llm_demo.assessment_insight", return_value=insight
        ) as interpretation:
            self.app.button(key="path_explore").click().run()
            self.app.toggle(key="use_ai").set_value(True).run()
            self.button("Show three opportunities").click().run()
            opportunities.assert_not_called()
            self.app.checkbox(key="ai_enrichment_authorized").check().run()
            self.button("Show three opportunities").click().run()
            opportunities.assert_called_once()
            self.app.button(key="choose_opportunity_0").click().run()
            self.button("Generate preliminary assessment").click().run()
            self.assertFalse(self.app.exception)
            interpretation.assert_called_once()
            self.assertEqual(self.app.session_state.assessment["ai_insight"], insight)
            self.assertEqual(self.app.session_state.assessment["solution_pattern"],
                             interpretation.call_args.args[0]["solution_pattern"])


if __name__ == "__main__":
    unittest.main()
