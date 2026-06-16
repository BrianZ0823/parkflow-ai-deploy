# ParkFlow AI 互联网部署

ParkFlow AI 需要前后端分离部署：

- 前端：静态站点，只包含 UI 和公开的后端 API 地址。
- 后端：Python API 服务，读取 `original V0` 数据，并在服务端使用 `DASHSCOPE_API_KEY` 调用模型。

不要把 `DASHSCOPE_API_KEY` 写进前端代码、`config.js`、浏览器 localStorage 或公开仓库。

## 本地 Docker 一键启动

在 `MVP DEMO` 目录下：

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up --build
```

Windows 也可以直接运行：

```powershell
.\deploy-internet.bat
```

打开：

```text
http://localhost:8080
```

后端健康检查：

```text
http://localhost:8765/api/health
```

## 云服务器部署

推荐先用任意支持 Docker Compose 的云服务器。

1. 上传整个 `parkflow-ai` 项目目录，必须包含：
   - `MVP DEMO`
   - `original V0`

2. 进入 `MVP DEMO`：

```bash
cp .env.example .env
nano .env
```

3. 修改 `.env`：

```env
DASHSCOPE_API_KEY=你的真实Key
PARKFLOW_API_BASE=https://api.your-domain.com
CORS_ALLOWED_ORIGINS=https://app.your-domain.com
FRONTEND_PORT=80
BACKEND_PORT=8765
```

4. 启动：

```bash
docker compose up -d --build
```

5. 域名建议：

```text
app.your-domain.com  -> frontend 容器 80
api.your-domain.com  -> backend 容器 8765
```

## 平台部署要点

如果使用 Render、Railway、Fly.io、阿里云、腾讯云或其他容器平台：

后端服务：

- Dockerfile：`MVP DEMO/deploy/backend.Dockerfile`
- Build context：项目根目录 `parkflow-ai`
- 环境变量：
  - `DASHSCOPE_API_KEY`
  - `DASHSCOPE_MODEL=qwen-plus`
  - `MVP_HOST=0.0.0.0`
  - `PARKFLOW_ORIGINAL_DIR=/app/original V0`
  - `CORS_ALLOWED_ORIGINS=https://你的前端域名`

后端 Dockerfile 只复制 `original V0` 的代码和数据目录，不复制 `original V0/api_key.txt`。线上密钥必须使用平台环境变量。

前端服务：

- Dockerfile：`MVP DEMO/deploy/frontend.Dockerfile`
- Build context：`MVP DEMO`
- 环境变量：
  - `PARKFLOW_API_BASE=https://你的后端域名`

## 安全边界

- 浏览器只能看到 `PARKFLOW_API_BASE`，看不到 `DASHSCOPE_API_KEY`。
- 所有模型调用都在后端完成。
- `original V0/api_key.txt` 不会被复制进后端镜像；线上必须使用平台环境变量 `DASHSCOPE_API_KEY`。
- `CORS_ALLOWED_ORIGINS` 只填写你的前端域名，不要用 `*`，除非临时调试。

## 验证

```bash
curl https://api.your-domain.com/api/health
```

返回中应看到：

```json
{
  "ok": true,
  "llm_configured": true,
  "model": "qwen-plus"
}
```
