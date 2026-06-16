---
name: Playwright网页搜索
version: 1.0.0
description: 使用 Playwright MCP 执行免费网页搜索并提取结果
triggers:
  keywords:
    - 搜索
    - 搜一下
    - 查一下
    - 帮我查
    - search
capabilities:
  - web_search
  - playwright_mcp
---

# Playwright 网页搜索 Skill

当用户要求“搜索/查一下”时，Skill 会优先使用 `mcp_playwright_*` 工具打开搜索引擎并提取结果。
