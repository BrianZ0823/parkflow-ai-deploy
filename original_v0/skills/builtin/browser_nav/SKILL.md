---
name: BrowserNavSkill
version: 1.0.0
description: |
  Integreates BrowserOS MCP to provide browser automation capabilities.
  Triggers on keywords like "search", "open", "browse", "visit".
triggers:
  keywords: ["search", "open", "browse", "visit", "google", "network"]
capabilities:
  - Web Search (via BrowserOS)
  - URL Navigation (via BrowserOS)
  - Page Interaction (via BrowserOS)
---

# Browser Navigation Skill

Allows the agent to control a browser instance via BrowserOS MCP.

## Capabilities

1.  **Search**: Perform Google searches and get results.
2.  **Navigate**: Open specific URLs.
3.  **Browse**: Interact with page content (click, type, scroll).

## How to Use

Simply say "Search for X" or "Open github.com".
If BrowserOS is running and connected, the agent will execute the command directly.

## Configuration

Requires `BROWSEROS_MCP_URL` environment variable (default: `http://localhost:3000/sse`).
