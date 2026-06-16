# ParkFlow AI 部署指南

## 前置要求

- Docker & Docker Compose（服务器或本地）
- DashScope API Key（阿里云通义千问）
- 服务器 CPU ≥ 2 核，内存 ≥ 4GB

## 快速部署（Docker Compose）

### 1. 克隆仓库

```bash
git clone <your-repo-url> parkflow
cd parkflow/MVP\ DEMO
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 DashScope API Key：

```ini
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1

FRONTEND_PORT=8080
BACKEND_PORT=8765
PARKFLOW_API_BASE=http://your-server-ip:8765
CORS_ALLOWED_ORIGINS=http://your-server-ip:8080
```

> **安全提示**：`.env` 文件包含 API Key，**切勿提交到 Git**。`.gitignore` 已排除 `.env`。

### 3. 启动服务

```bash
docker compose up -d --build
```

### 4. 访问

- 前端：`http://your-server-ip:8080`
- 后端 API：`http://your-server-ip:8765`

### 5. 查看日志

```bash
docker compose logs -f
```

## 独立部署（无 Docker）

### 后端

```bash
# 安装依赖
pip install -r deploy/backend-requirements.txt

# 配置环境
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export MVP_HOST=0.0.0.0
export MVP_PORT=8765

# 启动
cd mvp-app && python server.py
```

### 前端

使用任意静态文件服务器（nginx 等）指向 `mvp-app/static/` 目录。

配置 `static/config.js`：

```js
window.PARKFLOW_API_BASE = "http://your-server-ip:8765";
```

## 环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `DASHSCOPE_API_KEY` | 是 | — | 阿里云 DashScope API Key |
| `DASHSCOPE_MODEL` | 否 | `qwen-plus` | LLM 模型名 |
| `DASHSCOPE_API_BASE` | 否 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 端点 |
| `MVP_HOST` | 否 | `127.0.0.1` | 后端监听地址（Docker 设为 0.0.0.0） |
| `MVP_PORT` | 否 | `8765` | 后端端口 |
| `PARKFLOW_ORIGINAL_DIR` | 否 | `../original V0` | 数据目录 |
| `CORS_ALLOWED_ORIGINS` | 否 | `*` | 允许的前端域名 |

## 架构

```
┌─────────────┐     ┌──────────────┐
│  Nginx       │────▶│  Python      │
│  (静态文件)   │     │  (server.py) │
│  :8080       │     │  :8765       │
└─────────────┘     └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  DashScope   │
                    │  (LLM API)   │
                    └──────────────┘
```

## 数据持久化

ChromaDB 向量库在首次启动时从 `original V0/db/chromadb/` 加载。

如需保留运行时数据（对话历史等），可挂载 volume：

```yaml
volumes:
  - ./data/chromadb:/app/original V0/db/chromadb
```

## 健康检查

```bash
curl http://your-server:8765/api/health
# → {"ok": true, "llm_configured": true, ...}
```

## 故障排查

**问题：后端启动时 ChromaDB 初始化慢**
首次启动 ChromaDB 可能需要 10-30 秒加载 embed 模型。健康检查返回前请耐心等待。

**问题：前端报 CORS 错误**
确保 `CORS_ALLOWED_ORIGINS` 包含前端实际访问地址。

**问题：LLM 返回空或报错**
确认 `DASHSCOPE_API_KEY` 有效且有余额。DashScope 国内直连无需代理。
