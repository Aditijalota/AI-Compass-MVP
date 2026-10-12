# AI Compass v0.1

AI Compass is a Streamlit prototype for discovering business-process opportunities and comparing them with proportionate technology patterns. Guided mode works locally by default. Optional Replit AI Integrations for OpenAI can select bounded context-sensitive questions, generate opportunity suggestions, and provide a labeled assessment interpretation with a bounded pilot plan. The visible Python classifier remains responsible for the recommended solution pattern.

AI access uses the managed `AI_INTEGRATIONS_OPENAI_BASE_URL` and `AI_INTEGRATIONS_OPENAI_API_KEY` configuration; no personal API key is required. Usage is billed to Replit credits. The sidebar offers separate opt-in AI opportunity suggestions and assessment explanations, gated by a non-sensitive-input confirmation. Discovery question AI is controlled in Discovery Studio. AI failures are displayed, not disguised as generated answers.

## Run

From the workspace root:

```bash
python main.py
```

## Try it

1. Choose **I have a business problem**, **Explore my department**, or **I'm new to AI**.
2. Complete the six guided discovery exchanges, or generate a preliminary result earlier.
3. Review the recommended pattern, alternatives, missing information, readiness concerns, and next steps.
4. Open **Opportunity Dashboard** to search and reopen saved assessments. Three fictional assessments are seeded on first run.


## Optional conversational discovery

Guided mode is the default and uses previous saved answers to choose a focus for each of the six exchanges. It works with no LLM or integration configured. All original assessment fields remain available, including when AI is enabled.

In **Discovery Studio → Optional AI discovery**, confirm that saved inputs are fictional or authorized non-sensitive information, then enable AI. OpenAI `gpt-5.4-mini` through Replit AI Integrations selects one question ID from an exchange-specific, reviewed set. It cannot write arbitrary questions, change classification, or connect to business systems. Only saved intake and earlier answers are sent, capped at 600 characters per field. Current unsaved input is never sent.

Replit manages `AI_INTEGRATIONS_OPENAI_BASE_URL` and `AI_INTEGRATIONS_OPENAI_API_KEY`; do not hardcode credentials or supply a personal key. Usage is billed to Replit credits. The app explicitly labels model-selected questions and falls back to guided prompts if configuration is missing, a request fails, or the selection is invalid. Each selection is cached within the session to avoid repeat charges on reruns; editing earlier answers changes the next question's context. Consent and AI mode reset when starting a new discovery. Turning AI off preserves saved answers.

Live model access requires Replit-managed configuration in the running app. Offline and simulated-provider paths can be tested without credentials:

```bash
python -m unittest discover -s artifacts/ai-compass/tests -v
```
## Record a demo

In the sidebar, expand **Fictional demos for recording**. Load each of the three examples, complete the normal intake, and submit each exchange. Answers are prefilled but editable. Enable the relevant AI options and confirm non-sensitive inputs if you want live AI assistance; otherwise demos work locally. Discovery AI only receives saved intake and previous exchanges, not unsaved demo fields.

- Business problem: Operations purchase-order exceptions across systems, with human approval.
- Department exploration: HR policy lookup; choose the AI-generated policy/search opportunity.
- New to AI: Marketing weekly reporting; choose the AI-generated reporting opportunity.

Generate the assessment, show its AI interpretation and pilot plan, then reopen it from the dashboard. These scenarios demonstrate discovery and assessment—not live RAG retrieval, tool execution, or a deployed autonomous agent.

Assessments are stored in `artifacts/ai-compass/data/ai_compass.db`. The prototype is for fictional or authorized non-sensitive information only.
