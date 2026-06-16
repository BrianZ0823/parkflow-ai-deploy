# 能力盘点表

## 当前理解

`original V0` 是一个已具备后端 Agent 能力的 Python CLI 项目，核心链路为：

```text
用户输入
↓
RecruitmentAgent
↓
Skills 优先匹配
↓
本地 SQLite / 本地 JSON / 产业图谱 / ChromaDB / MCP 工具采集数据
↓
OpenAI-compatible DashScope LLM 生成最终回复
```

这与 `AI招商智能体 MVP计划.pdf` 中“允许模拟数据，不允许模拟系统”的原则基本一致。

但当前项目形态仍偏 CLI Agent + 静态原型页面，不是可直接演示的 AI Native 招商工作台。后续 MVP 应基于真实后端链路重新组织前端体验，不能直接使用静态原型里的硬编码结论。

## 与 MVP 计划是否一致

总体一致：

- 已有本地企业库、政策库、产业图谱、CRM、园区资源、外部情报 JSON。
- 已有 LLM 调用配置。
- 已有 Skills + Legacy Tools + MCP 的工具调用结构。
- 已有企业匹配和招商材料生成的多源数据采集链路。

存在偏差：

- 当前主要入口是 CLI，不是面向领导演示的 AI Native Web 工作台。
- `prototype/` 是静态页面，存在前端硬编码结果，不符合最终 MVP 的真实链路要求。
- 产业分析、政策分析目前更多是数据/工具能力，还没有完全包装为计划要求的结构化报告。
- RAG 检索代码存在，但查询需要 Embedding API 和完整依赖，当前验证环境无法直接跑通。

## 现有项目结构摘要

| 模块 | 位置 | 结论 |
|---|---|---|
| Agent 入口 | `original V0/main.py` | CLI 入口，初始化 SQLite、NetworkX、ChromaDB 后启动对话 |
| Agent 主循环 | `original V0/agent/agent_loop.py` | 加载 Skills、MCP、Legacy Tools，并调用 LLM |
| 工具定义 | `original V0/tools/definitions.py` | 定义企业检索、风险、产业链、园区资源、CRM、RAG、外部情报等工具 |
| 工具实现 | `original V0/tools/implementations.py` | 本地 SQLite / JSON / 图谱 / ChromaDB 数据读取 |
| Skills | `original V0/skills/builtin/` | 已有企业匹配、招商话术、报告生成、浏览器相关 Skills |
| MCP | `original V0/mcp_servers/` | 4 个本地 MCP server：SQLite、Vector KB、Industry Graph、External Intel |
| 本地数据库 | `original V0/db/park_data.db` | 企业、CRM、政策、园区资源数据 |
| 产业图谱 | `original V0/db/industry_graph.json` | 含产业节点、上下游关系、缺口分析 |
| 向量库 | `original V0/db/chromadb/` | ChromaDB 文件存在 |
| 静态原型 | `original V0/prototype/` | 可参考视觉和信息组织，但不能直接作为真实 Demo 结果 |

## 数据资产盘点

| 数据资产 | 位置 | 数量 | 是否本地真实数据 |
|---|---:|---:|---|
| 企业库 | SQLite `enterprises` | 188 | 是，本地模拟企业库 |
| CRM 记录 | SQLite `crm_records` | 87 | 是，本地模拟 CRM |
| 园区政策 | SQLite `park_policies` | 6 | 是，本地模拟政策库 |
| 园区资源 | SQLite `park_resources` | 10 | 是，本地模拟资源库 |
| 产业图谱 | `industry_graph.json` | 含节点、边、缺口分析 | 是，本地图谱 |
| 向量知识库 | `db/chromadb/` | 文件存在 | 未完全验证 |
| 外部情报 | `external_api/*.json` | 文件存在 | 本地模拟外部数据 |

## MVP 必需能力盘点

| 能力 | 是否可用 | 对应接口 / 代码 | 是否真实调用 | 风险 |
|---|---|---|---|---|
| 企业分析 | 基本可用 | `EnterpriseMatcherSkill`、`get_company_risk`、`query_crm_status`、`get_industry_chain`、`search_park_resources` | 是，采集本地企业/风险/CRM/图谱/资源后交给 LLM | 需改造成《目标企业招商研判报告》结构；产业图谱运行依赖需补齐 |
| 产业分析 | 部分可用 | `get_industry_chain`、`industry_graph_mcp/query_industry_chain` | 是，读取本地产业图谱 | 当前是工具结果，不是完整《产业链招商机会分析报告》；当前验证环境缺 `networkx` |
| 政策分析 | 部分可用 | `park_policies`、`search_park_resources(include_policies=True)`、`sqlite_db_mcp/query_policies` | 是，读取本地政策表 | 缺独立政策匹配报告 Skill；需要补“政策摘要、适用对象、招商价值、推荐企业”等结构 |
| 招商材料生成 | 基本可用 | `PitchWriterSkill` | 是，采集企业、CRM、政策、资源、新闻、相似案例后交给 LLM | 当前偏邮件/话术/方案，需扩展到邀请函、拜访提纲、电话话术、微信话术、汇报材料、推进计划 |
| RAG 检索 | 代码存在，当前未跑通 | `search_knowledge_base`、`vector_kb_mcp/semantic_search`、ChromaDB | 设计上是真实 Embedding + ChromaDB | 当前验证环境缺 `openai/chromadb`，且查询需 DashScope Embedding API；需在项目运行环境验证 |
| MCP 调用 | 代码存在，当前未跑通 | `mcp_client.py`、`mcp_servers/*/server.py` | 设计上是真实本地 MCP server | 当前验证环境缺 `mcp` 依赖；需在项目 Python 环境验证 |
| 来源引用 | 部分可用 | `search_knowledge_base` 返回 `citation`，本地工具返回政策/企业 ID | 部分真实 | 还未形成统一报告引用格式；需前端展示“数据来源” |
| 文件上传 | 未确认 | 未发现明确上传接口 | 未确认 | 当前 CLI/静态原型未体现上传能力；MVP 可暂不做或标记暂不支持 |
| 会话能力 | 基本可用 | `RecruitmentAgent.messages`、`reset()`、`ConversationLogger` | 是，内存会话 + 日志 | Web 化后需要会话 ID 或前端状态管理；当前不是 HTTP 会话 |

## 本地冒烟测试结果

测试范围：只读调用 `original V0/tools/implementations.py` 中不依赖外部网络和缺失包的工具。

| 工具 | 测试结果 | 说明 |
|---|---|---|
| `search_enterprises` | 通过 | 可从 SQLite 企业库返回候选企业 |
| `get_company_risk` | 通过 | 可返回本地风险评分与风险因子 |
| `search_park_resources` | 通过 | 可返回园区资源和政策 |
| `query_crm_status` | 通过 | 可返回企业跟进记录 |
| `get_external_intelligence` | 通过 | 可返回本地模拟工商/融资/专利情报 |
| `get_industry_chain` | 未在当前环境跑通 | 代码和图谱存在，但 Codex 自带 Python 缺 `networkx` |
| `search_knowledge_base` | 未在当前环境跑通 | 代码和 ChromaDB 文件存在，但当前环境缺 `openai/chromadb`，且需要 Embedding API |

当前验证环境缺少：

- `openai`
- `chromadb`
- `networkx`
- `mcp`
- `PyYAML`

这属于验证环境风险，不直接等同于旧项目不可用。`original V0/requirements.txt` 已声明这些依赖。

## 与 MVP 四大能力的落地判断

### 1. 企业分析

可作为第一优先级落地。

理由：

- 数据源最完整。
- 已有 Skill 采集企业、风险、CRM、产业链、资源、政策、相似案例。
- 最适合包装成领导能看懂的《目标企业招商研判报告》。

需要补齐：

- 固定报告结构。
- 来源引用。
- 行动建议和下一步材料生成。

### 2. 产业分析

可落地，但要轻量包装。

理由：

- 本地产业图谱和缺口分析存在。
- 对招商场景有强展示价值。

需要补齐：

- 产业链结构可视化。
- 龙头企业/关键环节/本地现状/机会点/优先级报告结构。
- 补齐运行依赖验证。

### 3. 政策分析

可作为辅助能力落地。

理由：

- SQLite 中已有政策表。
- 可与企业行业、资质、规模做匹配。

需要补齐：

- 独立政策分析入口。
- 政策匹配逻辑。
- 《政策匹配分析报告》结构。

### 4. 招商材料生成

可作为 Demo 亮点落地。

理由：

- 已有 PitchWriterSkill。
- 与企业分析结果天然衔接。

需要补齐：

- 材料类型选择。
- 与报告结果联动。
- 输出为“可直接拿去用”的文本，而不是普通聊天回复。

## 主要风险点

| 风险 | 影响 | 建议 |
|---|---|---|
| 前端静态原型硬编码结果 | 违反“不允许模拟系统”原则 | 只参考视觉，不直接复用其数据逻辑 |
| 当前没有 Web API 层 | 难以形成可演示工作台 | 需新增薄 API 层或包装 CLI Agent 调用 |
| 后端依赖未在当前验证环境安装 | 无法完整验证 RAG/MCP/图谱 | 后续在项目运行环境补依赖并做最小验证 |
| 产业/政策缺完整报告 Skill | 输出容易变成工具结果或聊天文本 | 新增轻量报告编排，不重构核心后端 |
| LLM 和 Embedding 依赖 DashScope API | Demo 稳定性受网络/API Key 影响 | 增加超时、错误提示和“当前能力暂不支持”状态 |
| `update_crm_record` 会写数据库 | Demo 中可能误改旧数据 | MVP 阶段默认不调用写入工具，或复制数据到 `MVP DEMO` 后使用 |

## 建议方案

下一阶段先输出三套产品方案，但从能力盘点看，最稳的方向应围绕：

> 一个任务式 AI 工作台：用户输入招商任务，系统展示“检索中、分析中、研判中、生成材料中”的过程，最终输出结构化招商研判报告和可执行材料。

优先 Demo 链路建议：

```text
输入：分析“未来芯片科技”是否适合招商，并生成下一步拜访材料
↓
企业画像
↓
风险分析
↓
产业链位置和园区缺口
↓
政策/资源匹配
↓
招商判断
↓
行动建议
↓
生成拜访提纲 / 微信跟进话术
```

## 下一步计划

进入阶段 2：输出三套完全不同的 AI Native 产品方案。

每套方案将包含：

- 设计理念
- 用户旅程
- 页面结构
- 核心交互
- 优势
- 风险
- 为什么适合招商场景

并推荐最适合 48 小时落地、最容易打动领导的方案。

