# MVP 前后端对接方案

## 当前选择

本次 MVP 采用独立薄 API 层：

```text
MVP DEMO/mvp-app/server.py
```

它只读调用 `original V0` 的本地数据资产，不修改 `original V0`，不重构旧 Agent，不改数据库结构。

## 为什么这样做

符合 `AI招商智能体 MVP计划.pdf` 的后端冻结原则：

- 不重构 LangGraph / RAG / MCP。
- 不修改核心业务流程。
- 不写入旧数据库。
- 只做 API 联调、错误处理、来源引用和演示稳定性优化。

同时满足 MVP 真实链路要求：

```text
前端自然语言任务
↓
真实 HTTP API
↓
本地企业库 / CRM / 政策库 / 产业图谱 / 风险数据
↓
真实 DashScope LLM
↓
结构化招商研判报告 / Artifact 材料
```

## 当前接口

| 接口 | 用途 | 是否真实链路 |
|---|---|---|
| `GET /api/health` | 检查服务、数据库、LLM 配置 | 是 |
| `GET /api/companies` | 查询本地企业库 | 是 |
| `POST /api/analyze` | 生成招商研判报告 | 是，本地数据 + LLM |
| `POST /api/material` | 生成招商材料 | 是，报告上下文 + LLM |

## 数据来源

| 能力 | 数据源 |
|---|---|
| 企业分析 | `enterprises`、`risk_data.json`、`company_intelligence.json`、`crm_records` |
| 产业分析 | `industry_graph.json` |
| 政策分析 | `park_policies` |
| 招商材料生成 | 当前报告上下文 + CRM 联系人 + 政策/资源/风险来源 |

## 后续正式集成建议

1. 将 `mvp-app/server.py` 的数据采集函数拆成服务层。
2. 将 `generate_report` 和 `generate_material` 的 prompt 固化为可版本管理模板。
3. 接入旧项目 `RecruitmentAgent` 的 Skills/MCP 时，只作为后端能力增强，不改变前端体验。
4. 增加会话 ID，用于记录一次招商任务的上下文、报告和材料。
5. 增加导出功能：Markdown / Word / PDF。
6. 增加“来源展开”面板，显示每条结论引用了哪些本地字段。

## 风险与处理

| 风险 | 当前处理 |
|---|---|
| DashScope 网络或 Key 不可用 | 接口返回错误，前端明确提示，不展示假结论 |
| 模型未返回 JSON | 保留真实模型原文并标记低置信度 |
| 企业未命中 | 返回 404 和本地企业库未找到提示 |
| 旧依赖不完整 | MVP 不依赖旧项目 Python 包，只读其数据文件 |
| 误写旧库 | 当前服务不调用写入接口 |
