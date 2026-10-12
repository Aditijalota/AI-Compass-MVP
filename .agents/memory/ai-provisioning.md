---
name: AI integration provisioning availability
description: Distinguish missing agent provisioning capability from an unavailable AI provider.
---

The AI integration setup action documented in the provider skill may not be exposed in the assigned-task environment. An empty connector search does not establish that Replit AI Integrations is unavailable platform-wide.

**Why:** The documented setup action was not registered in this workspace's task runtime, while official documentation still described managed OpenAI access. No user credentials should be requested to work around that limitation.

**How to apply:** Use the provider skill's managed configuration boundary, explicitly disclose unconfigured status, and keep offline behavior functional. Do not claim a successful live model test when only simulated-provider checks were possible.
