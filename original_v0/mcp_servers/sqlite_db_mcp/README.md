# SQLite Database MCP Server

为园区招商系统提供标准Model Context Protocol (MCP) 访问接口

## 功能

提供 4 个工具:
- `search_enterprises`: 搜索企业
- `search_park_resources`: 搜索园区资源  
- `query_policies`: 查询政策
- `query_crm_status`: 查询CRM状态

## 使用方法

### 独立运行测试
```bash
python server.py
```

### 在 Agent 中使用
参考主项目的 MCP 客户端集成代码

## 数据源

- 数据库: `../../db/park_data.db`
- 包含: 企业、园区资源、政策、CRM 数据
