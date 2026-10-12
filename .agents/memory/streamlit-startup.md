---
name: Streamlit unattended startup
description: First-run onboarding, artifact working directories, and shared-preview routing.
---

Streamlit may pause on its first-run email opt-in prompt before opening its server port.

**Why:** An unattended workflow timed out with only the onboarding email prompt in its output; headless startup served normally.

**How to apply:** When a new Streamlit workflow reports that no port opened, check the console for an email prompt before changing ports or networking. Use headless startup for managed workflows.

A standalone webview workflow does not necessarily register a root route in a path-routed workspace.

**Why:** The process served normally but the shared proxy returned "Backend Not Configured" until it was registered as a web artifact service.

**How to apply:** Confirm the app through the shared preview proxy, not just its local port. Register its managed service and WebSocket path using validated artifact configuration when the proxy has no route.

Managed artifact service commands run from the artifact directory, not necessarily the workspace root.

**Why:** A root-relative launcher command attempted to open a nonexistent file under the artifact directory.

**How to apply:** Use a launcher with explicit paths or change to the workspace root when a service needs root-level files.
