# ParkFlow AI 招商助手 MVP

ParkFlow AI 是面向招商局、产业园区、城投平台和招商负责人的 AI Native 招商助手。

用户不需要操作一套管理系统，只要直接说出目标：找企业、看机会、写材料、继续推进。

## 当前形态

- 单一自然语言入口：所有输入都交给服务端处理，前端不抢先判断。
- 一屏工作区：左侧交流，右侧工作成果，底部持续输入。
- 过程可感知：办理中展示关键进展，完成后自动收起。
- 工作成果优先：回答、资料概览、企业建议、招商材料会成为主视图。
- 按需展开：参考资料、下一步推进、招商材料包只在需要时打开。

## 当前支持场景

- 找优先企业
- 看一家企业是否值得推进
- 分析产业机会
- 查询资料覆盖情况
- 生成拜访提纲、微信话术、领导汇报、推进计划、邀请函

## 启动

```powershell
D:\MyCodingProject\parkflow-ai\MVP DEMO\mvp-app\start-server.bat
```

打开：

[http://127.0.0.1:8765/](http://127.0.0.1:8765/)

## 主要接口

```http
GET /api/health
GET /api/stats
POST /api/message_stream
POST /api/material
```

前端统一把用户输入交给 `/api/message_stream`，服务端决定进入普通回答、资料概览、企业建议或材料生成。

## 演示任务

```text
你是谁？你能帮招商人员做什么？
```

```text
我想找一些对园区有贡献、租金承载力不错、未来有发展的企业，先推荐 8 家并说明理由
```

```text
分析未来芯片科技是否值得重点招商，并生成拜访材料。
```

## 验证命令

```powershell
C:\Users\Brian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m py_compile "D:\MyCodingProject\parkflow-ai\MVP DEMO\mvp-app\server.py"
node --check "D:\MyCodingProject\parkflow-ai\MVP DEMO\mvp-app\static\app.js"
```
