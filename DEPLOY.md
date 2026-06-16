# ParkFlow AI 部署指南

## 架构

```
用户 → Netlify CDN（前端静态文件）
         → config.js → PARKFLOW_API_BASE
         → Railway（后端 Python 服务）
              → DashScope API（LLM 通义千问）
              → local SQLite / ChromaDB（企业数据）
```

---

## 生产环境配置（当前使用）

### 前端 — Netlify

| 项目 | 值 |
|---|---|
| 仓库 | `BrianZ0823/parkflow-ai-deploy` |
| 站点 | `https://fancy-phoenix-0b5362.netlify.app` |
| 构建命令 | `node deploy/write-frontend-config.mjs`（由 `netlify.toml` 自动设置）|
| 发布目录 | `mvp-app/static` |
| 环境变量 | `PARKFLOW_API_BASE=https://parkflow-ai-deploy-production.up.railway.app` |

### 后端 — Railway

| 项目 | 值 |
|---|---|
| 项目名 | `parkflow-ai-deploy` |
| 构建方式 | Docker（`deploy/backend.Dockerfile`）|
| 服务域名 | `https://parkflow-ai-deploy-production.up.railway.app` |
| 环境变量 | |

| 变量 | 值 |
|---|---|
| `DASHSCOPE_API_KEY` | `sk-66a6fcac623a475d99b9fa23b85d07c0` |
| `DASHSCOPE_MODEL` | `qwen-plus` |
| `DASHSCOPE_API_BASE` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `MVP_HOST` | `0.0.0.0` |
| `MVP_PORT` | `8765` |
| `CORS_ALLOWED_ORIGINS` | `*` |

---

## 修改代码后如何更新

### 1. 修改代码并推送

```bash
git add -A
git commit -m "修改内容说明"
git push
```

### 2. 前端（Netlify 自动部署）

推送后 Netlify 会自动检测变更并重新部署，**无需手动操作**。
可在 [Netlify Dashboard](https://app.netlify.com) 查看构建状态。

### 3. 后端（Railway 手动触发）

方式一：在 Railway Dashboard 点 **Redeploy**

方式二：命令行

```bash
railway login      # 浏览器授权 GitHub
cd parkflow-ai/MVP\ DEMO
railway up
```

---

## 本地开发

```bash
# 安装后端依赖
pip install -r deploy/backend-requirements.txt

# 配置 API Key
export DASHSCOPE_API_KEY=sk-66a6fcac623a475d99b9fa23b85d07c0

# 启动后端
cd mvp-app && python server.py
# 访问 http://127.0.0.1:8765

# 前端直接在浏览器打开 mvp-app/static/index.html
# 或任意静态文件服务器指向 static 目录
```

---

## 环境变量参考

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `DASHSCOPE_API_KEY` | 是 | — | 阿里云 DashScope API Key |
| `DASHSCOPE_MODEL` | 否 | `qwen-plus` | LLM 模型名 |
| `DASHSCOPE_API_BASE` | 否 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 端点 |
| `MVP_HOST` | 否 | `127.0.0.1` | 后端监听地址 |
| `MVP_PORT` | 否 | `8765` | 后端端口 |
| `PARKFLOW_API_BASE` | 是（前端） | — | 后端公网地址，前端通过它调用 API |
| `CORS_ALLOWED_ORIGINS` | 否 | `*` | 允许跨域的前端域名 |

## 健康检查

```bash
curl https://parkflow-ai-deploy-production.up.railway.app/api/health
# → {"ok": true, "llm_configured": true, ...}
```
