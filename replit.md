# AI Compass

AI Compass is a Streamlit prototype that helps individuals, managers, business owners, and consultants discover process-improvement opportunities and compare them with proportionate software, automation, or AI patterns.

## Run & Operate

- Streamlit app: `python main.py` — uses headless startup and the workflow-provided `PORT`, or port 5000 when run manually.
- Python packages: `artifacts/ai-compass/requirements.txt`
- Local prototype storage: `artifacts/ai-compass/data/ai_compass.db` (SQLite, created on first run)
- Live AI discovery uses Replit-managed OpenAI configuration; no personal API key or `DATABASE_URL` is required. AI usage is billed to Replit credits.
- Existing workspace tooling: `pnpm run typecheck`

## Stack

- Python, Streamlit, Pandas, and SQLite for the AI Compass prototype.
- The workspace also contains shared pnpm/TypeScript API and design-sandbox artifacts.

## Where things live

- `artifacts/ai-compass/app.py` — Streamlit pages and user interactions.
- `artifacts/ai-compass/discovery.py` — guided prompts and opportunity suggestions.
- `artifacts/ai-compass/classification.py` — explainable solution-fit rules.
- `artifacts/ai-compass/database.py` — SQLite schema, example data, and persistence.
- `artifacts/ai-compass/models.py` — assessment data model.
- `artifacts/ai-compass/reports.py` — assessment text and JSON exports.

## Architecture decisions

- The MVP follows the requested Python/Streamlit stack and keeps UI, discovery, classification, persistence, and reporting in separate modules.
- Live AI discovery is enabled by default for demos; recommendations retain local, deterministic rules as their authority. An LLM supplies opportunities, adaptive questions, and an explicitly labeled interpretation.
- SQLite is local prototype storage and should not be treated as a multi-user production database.
- Fictional sample records are included; users should not enter confidential or personal data.

## Product

- Three intake pathways share a six-exchange discovery workflow.
- Each assessment explains its recommendation, alternatives, expected benefits, missing inputs, readiness concerns, and next steps.
- The dashboard offers grouped counts, search, and assessment reopening.

## User preferences

- The user asked for a working Streamlit MVP and explicitly said not to publish automatically.

## Gotchas

- The app runs through the managed `artifacts/ai-compass-preview: web` workflow. Its preview registration is in `artifacts/ai-compass-preview/`; all application code remains Python/Streamlit.
- The prompt limits v0.1 to fictional or authorized non-sensitive information and no external business-system integrations.

## Pointers

- See `artifacts/ai-compass/README.md` for local run and smoke-test steps.
