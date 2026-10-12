# AI Compass v0.1

AI Compass is a Streamlit prototype for discovering business-process opportunities and comparing them with proportionate technology patterns. Live LLM-powered discovery is enabled by default through Replit AI Integrations for OpenAI. It generates opportunities, context-sensitive follow-up questions, and an assessment interpretation with a bounded pilot plan. The visible Python classifier remains responsible for the recommended solution pattern.

AI access uses the managed `AI_INTEGRATIONS_OPENAI_BASE_URL` and `AI_INTEGRATIONS_OPENAI_API_KEY` configuration; no personal API key is required. Usage is billed to Replit credits. The sidebar toggle offers an explicit local guided mode. AI failures are displayed, not disguised as generated answers.

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

## Record a demo

In the sidebar, expand **Fictional demos for recording**. Load each of the three examples, complete the normal intake, and submit each exchange. Answers are prefilled but editable; AI only receives answers after they are submitted.

- Business problem: Operations purchase-order exceptions across systems, with human approval.
- Department exploration: HR policy lookup; choose the AI-generated policy/search opportunity.
- New to AI: Marketing weekly reporting; choose the AI-generated reporting opportunity.

Generate the assessment, show its AI interpretation and pilot plan, then reopen it from the dashboard. These scenarios demonstrate discovery and assessment—not live RAG retrieval, tool execution, or a deployed autonomous agent.

Assessments are stored in `artifacts/ai-compass/data/ai_compass.db`. The prototype is for fictional or authorized non-sensitive information only.
