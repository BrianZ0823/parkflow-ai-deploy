# AI 招商智能体 MVP App

这是 `MVP DEMO` 下的独立可运行 MVP，不修改 `original V0`。

## 启动方式

```powershell
cd "D:\MyCodingProject\parkflow-ai\MVP DEMO\mvp-app"
python server.py
```

如果命令行没有 `python`，可使用 Codex 桌面内置 Python：

```powershell
& "C:\Users\Brian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "D:\MyCodingProject\parkflow-ai\MVP DEMO\mvp-app\server.py"
```

浏览器打开：

```text
http://127.0.0.1:8765
```

## 真实链路

```text
用户自然语言任务
↓
前端 POST /api/analyze
↓
后端只读 original V0 本地 SQLite / JSON / 产业图谱
↓
DashScope OpenAI-compatible LLM 生成结构化招商研判报告
↓
前端展示报告、来源和可继续生成的 Artifact 材料
```

## 已接入数据源

- `original V0/db/park_data.db`
  - `enterprises`
  - `crm_records`
  - `park_policies`
  - `park_resources`
- `original V0/db/industry_graph.json`
- `original V0/external_api/risk_data.json`
- `original V0/external_api/company_intelligence.json`

## API

### `GET /api/health`

检查数据库、LLM 配置和只读状态。

### `GET /api/companies?q=芯片`

查询本地企业库。

### `POST /api/analyze`

请求：

```json
{
  "task": "分析未来芯片科技是否值得重点招商，并生成拜访材料。"
}
```

返回：

- `context`：真实命中的本地数据
- `sources`：来源清单
- `report`：LLM 生成的结构化招商研判报告

### `POST /api/material`

请求：

```json
{
  "task": "分析未来芯片科技是否值得重点招商，并生成拜访材料。",
  "type": "wechat",
  "report": {}
}
```

支持类型：

- `outline`：企业拜访提纲
- `wechat`：微信跟进话术
- `briefing`：领导汇报材料
- `risk`：风险复核清单
- `plan`：项目推进计划
- `invite`：招商邀请函
- `phone`：电话沟通话术

## 边界说明

- 不使用 Mock API。
- 不在前端硬编码报告或结论。
- LLM 不可用时接口返回错误，前端提示“不会使用假报告兜底”。
- 当前 MVP 不调用 `update_crm_record`，避免写入 `original V0` 数据库。
