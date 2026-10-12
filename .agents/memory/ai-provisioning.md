---
name: AI integration provisioning availability
description: Distinguish missing agent provisioning capability from an unavailable AI provider.
---

The AI integration setup action documented in the provider skill may not be exposed in the assigned-task environment. An empty connector search does not establish that Replit AI Integrations is unavailable platform-wide.

**Why:** The documented setup action was not registered in this workspace's task runtime, while official documentation still described managed OpenAI access. No user credentials should be requested to work around that limitation.

**How to apply:** Use the provider skill's managed configuration boundary and keep offline behavior functional. Check configuration presence without exposing values: existing managed configuration can support live access even when the setup action is absent. Only report unconfigured status when configuration is actually missing. Do not claim a successful live model test when only simulated-provider checks were possible.

Live smoke tests must explicitly opt in to billed requests and treat guided fallback as a failed live check.

**Why:** A missing SDK can cause the app to render successfully in guided mode even with managed configuration present; successful rendering alone does not prove live AI access.

**How to apply:** Require a valid provider-selected question and model label, isolate storage with fictional inputs, count real calls to verify session reuse, and inject failure separately without extra billed requests.
