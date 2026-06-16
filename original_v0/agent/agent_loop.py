# -*- coding: utf-8 -*-
"""Agent 主循环 —— 基于 OpenAI-compatible Function Calling + Skills"""
import json
import os
import sys
import logging
from openai import OpenAI
from agent.config import LLM_CONFIG, CHARACTER_MODEL_CONFIG
from agent.system_prompt import build_system_prompt
from agent.logger import ConversationLogger
from agent.tracing import TracingSpan
from tools.definitions import TOOL_DEFINITIONS
from tools.executor import execute_tool

logger = logging.getLogger(__name__)

# 导入 Skills
try:
    from skills.skill_manager import SkillManager
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False
    logger.warning("[Agent] Skills 模块未找到，将仅使用 Function Calling")

# 导入 MCP 客户端
try:
    from mcp_client import MCPClientWrapper
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("[Agent] MCP 客户端未找到，将仅使用 Legacy Function Calling")

# Agent 配置常量
MAX_TOOL_CALL_ROUNDS = 15  # 防止无限循环的最大工具调用次数

# MCP 服务器配置
MCP_SERVER_CONFIGS = [
    {
        "name": "sqlite_db",
        "command": sys.executable,
        "server_path": "mcp_servers/sqlite_db_mcp/server.py"
    },
    {
        "name": "vector_kb",
        "command": sys.executable,
        "server_path": "mcp_servers/vector_kb_mcp/server.py"
    },
    {
        "name": "industry_graph",
        "command": sys.executable,
        "server_path": "mcp_servers/industry_graph_mcp/server.py"
    },
    {
        "name": "external_intel",
        "command": sys.executable,
        "server_path": "mcp_servers/external_intel_mcp/server.py"
    },
]

# Playwright MCP 配置（免费，无需 API Key）
ENABLE_PLAYWRIGHT_MCP = os.getenv("ENABLE_PLAYWRIGHT_MCP", "1").lower() in ("1", "true", "yes", "on")
if ENABLE_PLAYWRIGHT_MCP:
    # 默认使用 headed 模式，降低搜索引擎反爬拦截概率。
    playwright_args = ["@playwright/mcp@latest", "--isolated"]
    if os.getenv("PLAYWRIGHT_MCP_HEADLESS", "0").lower() in ("1", "true", "yes", "on"):
        playwright_args.append("--headless")
    MCP_SERVER_CONFIGS.append({
        "name": "playwright",
        "command": "npx",
        "args": playwright_args
    })


class RecruitmentAgent:
    """招商经理智能体"""

    def __init__(self):
        self.client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["api_base"],
            timeout=LLM_CONFIG.get("timeout", 45),
            max_retries=LLM_CONFIG.get("max_retries", 2),
        )
        self.model = LLM_CONFIG["model"]
        self.temperature = LLM_CONFIG["temperature"]
        self.max_tokens = LLM_CONFIG["max_tokens"]
        self.messages = []
        self.logger = ConversationLogger()  # 初始化日志记录器

        # 表达层客户端（qwen-plus-character），负责生成用户可见的最终回复
        self.character_client = OpenAI(
            api_key=CHARACTER_MODEL_CONFIG["api_key"],
            base_url=CHARACTER_MODEL_CONFIG["api_base"],
            timeout=CHARACTER_MODEL_CONFIG.get("timeout", 45),
            max_retries=CHARACTER_MODEL_CONFIG.get("max_retries", 2),
        )
        self.character_model = CHARACTER_MODEL_CONFIG["model"]
        self.character_temperature = CHARACTER_MODEL_CONFIG["temperature"]
        self.character_max_tokens = CHARACTER_MODEL_CONFIG["max_tokens"]
        
        # 初始化 Skills Manager
        self.skill_manager = None
        if SKILLS_AVAILABLE:
            try:
                self.skill_manager = SkillManager()
                self.skill_manager.load_builtin_skills()
                logger.info("[Agent] 已加载 %d 个 Skills", len(self.skill_manager.skills))
            except Exception as e:
                logger.exception("[Agent] Skills 初始化失败: %s", e)
        
        # 初始化 MCP 客户端
        self.mcp_client = None
        if MCP_AVAILABLE:
            try:
                self.mcp_client = MCPClientWrapper()
                # 配置 MCP 服务器（使用配置常量）
                base_dir = os.path.dirname(os.path.dirname(__file__))
                
                # 准备环境变量（确保子进程有 API Key）
                mcp_env = os.environ.copy()
                if "DASHSCOPE_API_KEY" not in mcp_env and LLM_CONFIG.get("api_key"):
                    mcp_env["DASHSCOPE_API_KEY"] = LLM_CONFIG["api_key"]
                
                mcp_servers = []
                for config in MCP_SERVER_CONFIGS:
                    if config.get("command") == "sse":
                         mcp_servers.append({
                            "name": config["name"],
                            "command": config["command"],
                            "args": config["args"],
                            "env": mcp_env
                        })
                    elif config.get("command") in ("http", "url"):
                        mcp_servers.append({
                            "name": config["name"],
                            "command": config["command"],
                            "args": config["args"],
                            "env": mcp_env
                        })
                    else:
                        # Stdio server with server_path
                        server_args = list(config.get("args", []))
                        if config.get("server_path"):
                            server_args = [os.path.join(base_dir, config["server_path"])] + server_args

                        mcp_servers.append({
                            "name": config["name"],
                            "command": config["command"],
                            "args": server_args,
                            "env": mcp_env
                        })
                self.mcp_client.initialize(mcp_servers)
                logger.info("[Agent] 已连接到 %d 个 MCP 服务器", len(mcp_servers))
            except Exception as e:
                logger.exception("[Agent] MCP 客户端初始化失败: %s", e)
                self.mcp_client = None
        
        self._init_system_prompt()

    def _init_system_prompt(self):
        """初始化动态 System Prompt"""
        prompt = build_system_prompt()
        self.messages = [{"role": "system", "content": prompt}]
        # 记录 System Prompt
        self.logger.log_system_prompt(prompt) 

    def _get_all_tools(self):
        """获取所有工具定义（Legacy + MCP）"""
        tools = list(TOOL_DEFINITIONS)  # Legacy tools
        
        # 添加 MCP 工具
        if self.mcp_client:
            mcp_tools = self.mcp_client.get_all_tools()
            tools.extend(mcp_tools)
        
        return tools
    
    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """执行工具（路由到 Legacy 或 MCP）"""
        # 判断是 MCP 工具还是 Legacy 工具
        if tool_name.startswith("mcp_"):
            # MCP 工具
            if self.mcp_client:
                return self.mcp_client.call_tool(tool_name, arguments)
            else:
                return json.dumps({"error": "MCP 客户端未初始化"}, ensure_ascii=False)
        else:
            # Legacy 工具
            return execute_tool(tool_name, arguments)

    def _build_expression_messages(self, max_history: int = 60) -> list:
        """为 Character 模型构建精简消息列表（控制在 32K 上下文以内）。
        
        策略：
        - 始终保留第一条 system 消息（人设/背景）
        - 最多保留最近 max_history 条消息
        - tool 角色消息内容截断至 2000 字符，避免工具结果 JSON 爆炸
        """
        if not self.messages:
            return self.messages
        system_msg = self.messages[0]  # 始终保留 system prompt
        recent = self.messages[1:][-max_history:]  # 取最近 N 条

        trimmed = []
        for msg in recent:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if len(content) > 2000:
                    msg = {**msg, "content": content[:2000] + "\n...(内容已截断，完整数据已用于推理)"}
            trimmed.append(msg)

        return [system_msg] + trimmed

    def _stream_character_answer(self, on_stream_chunk=None) -> str:
        """用 qwen-plus-character 生成最终用户可见回复（真实流式输出）。
        
        表达层：推理阶段（qwen-plus）已完成工具调用和信息收集，
        本方法仅负责以招商经理的口吻流式输出最终回复。
        """
        logger.info("[Agent] 表达层：调用 %s 生成最终回复", self.character_model)
        content_parts = []
        try:
            stream = self.character_client.chat.completions.create(
                model=self.character_model,
                messages=self._build_expression_messages(),
                temperature=self.character_temperature,
                max_tokens=self.character_max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                piece = delta.content or ""
                if not piece:
                    continue
                content_parts.append(piece)
                if on_stream_chunk:
                    on_stream_chunk(piece)
        except Exception as e:
            logger.warning("[Agent] Character 模型流式输出失败，回退到推理模型: %s", e)
            # 回退：读取 messages 中最后一条 assistant 内容
            for msg in reversed(self.messages):
                if msg.get("role") == "assistant" and msg.get("content"):
                    fallback = msg["content"]
                    if on_stream_chunk:
                        self._emit_text_as_stream(fallback, on_stream_chunk)
                    return fallback
        return "".join(content_parts).strip()

    def _stream_final_answer(self, on_stream_chunk=None) -> str:
        """以流式方式生成最终回复文本（推理层，保留作为内部备用）。"""
        content_parts = []
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self._get_all_tools(),
            tool_choice="none",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            piece = delta.content or ""
            if not piece:
                continue
            content_parts.append(piece)
            if on_stream_chunk:
                on_stream_chunk(piece)

        return "".join(content_parts).strip()

    def _emit_text_as_stream(self, text: str, on_stream_chunk=None, chunk_size: int = 48):
        """将已有文本按分块回调，统一终端显示为流式。"""
        if not text or not on_stream_chunk:
            return
        for i in range(0, len(text), chunk_size):
            on_stream_chunk(text[i:i + chunk_size])
    
    def chat(self, user_input: str, on_stream_chunk=None) -> str:
        """处理一轮用户输入，返回最终回复"""
        with TracingSpan("agent_chat_turn", {"user.input": user_input[:200]}) as chat_span:
            self.logger.log_user_input(user_input)  # 记录用户输入
            self.messages.append({"role": "user", "content": user_input})
            
            # ===== 优先检查 Skills 是否可以直接处理 =====
            if self.skill_manager:
                context = {
                    "user_input": user_input,
                    "history": self.messages,
                    "mcp_client": self.mcp_client,  # 注入 MCP 客户端供 Skill 使用
                }
                matching_skills = self.skill_manager.find_matching_skills(context)
                
                if matching_skills:
                    skill_name = matching_skills[0].name
                    print(f"  [Skill] 匹配到 Skill: {skill_name}")
                    with TracingSpan("skill_execution", {"skill.name": skill_name}):
                        try:
                            result = matching_skills[0].execute(context)
                            
                            if result.get("handled"):
                                # ── 数据报告型 Skill（如报告生成器）→ 经 Character 模型润色后流式输出 ──
                                skill_draft = result["response"]
                                print(f"  [Skill] {skill_name} 生成草稿，交由 Character 模型润色输出")
                                # 将 Skill 草稿注入为 system 消息，让 Character 模型做细微润色
                                self.messages.append({
                                    "role": "system",
                                    "content": (
                                        f"[Skill草稿 — {skill_name}]\n"
                                        f"以下是系统生成的草稿，请在完整保留所有数据、结构和格式的前提下，"
                                        f"仅对措辞做细微优化（如去掉生硬的模板语气），不得增删任何数据或调整章节结构。\n\n"
                                        f"{skill_draft}"
                                    )
                                })
                                final_content = self._stream_character_answer(on_stream_chunk)
                                self.messages.append({"role": "assistant", "content": final_content})
                                self.logger.log_agent_response(
                                    final_content,
                                    metadata={"skill_used": skill_name, "expression_model": self.character_model}
                                )
                                chat_span.set_attribute("resolution", "skill_character")
                                chat_span.set_attribute("skill.name", skill_name)
                                return final_content
                            
                            elif result.get("context_data"):
                                # ── 数据采集型 Skill → 注入上下文，交给 LLM ──
                                context_data = result["context_data"]
                                instruction = result.get("instruction", "请基于以上数据进行分析。")
                                skill_data = result.get("data", {})
                                
                                print(f"  [Skill] {skill_name} 采集了 {len(context_data)} 项数据，交给 LLM 处理")
                                
                                # 注入 Skill 采集的数据为 system message
                                data_summary = json.dumps(context_data, ensure_ascii=False, indent=2)
                                self.messages.append({
                                    "role": "system",
                                    "content": (
                                        f"[Skill数据注入 — {skill_data.get('skill_name', skill_name)}]\n"
                                        f"以下是由 Skill 自动采集的结构化数据，请基于这些真实数据完成用户的请求。\n"
                                        f"绝对不要忽略这些数据，也不要编造不在数据中的内容。\n\n"
                                        f"---\n{data_summary}\n---\n\n"
                                        f"任务指令：{instruction}"
                                    )
                                })
                                
                                chat_span.set_attribute("skill.context_injected", skill_name)
                                # 不 return，继续到 LLM 循环
                        except Exception as e:
                            logger.warning("[Skill] 执行失败，回退到 LLM: %s", e)

            # 可能需要多轮工具调用
            max_rounds = MAX_TOOL_CALL_ROUNDS
            total_tool_calls = 0
            for i in range(max_rounds):
                # 记录发送给 LLM 的完整 Context (Prompt + History)
                self.logger.log_request_payload(self.messages)

                # 如果是最后一次尝试，强制不使用工具，让模型总结
                current_tool_choice = "auto"
                if i == max_rounds - 1:
                    current_tool_choice = "none"
                    self.messages.append({
                        "role": "system",
                        "content": "System: You have reached the maximum number of steps. Please stop using tools and provide your best answer based on the information you have so far."
                    })

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self._get_all_tools(),  # 使用合并的工具列表
                    tool_choice=current_tool_choice,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                msg = response.choices[0].message
                
                # 记录 Agent 思考/行动
                tool_calls_data = None
                if msg.tool_calls:
                    tool_calls_data = [
                        {"name": tc.function.name, "arguments": tc.function.arguments}
                        for tc in msg.tool_calls
                    ]
                
                # 如果没有工具调用，交由 Character 模型生成最终回复（表达层）
                if not msg.tool_calls:
                    # 将推理模型的思考内容（如有）先记录，但不直接输出给用户
                    if msg.content:
                        self.messages.append({"role": "assistant", "content": msg.content})
                    # 表达层：用 qwen-plus-character 真实流式生成用户可见回复
                    final_content = self._stream_character_answer(on_stream_chunk)
                    if not final_content and msg.content:
                        # Character 模型无输出时回退到推理模型结果
                        final_content = msg.content
                        if on_stream_chunk:
                            self._emit_text_as_stream(final_content, on_stream_chunk)

                    if not msg.content:
                        # 推理模型无中间内容时才补追加 assistant 消息
                        self.messages.append({"role": "assistant", "content": final_content})
                    self.logger.log_agent_response(
                        final_content,
                        metadata={"expression_model": self.character_model}
                    )
                    chat_span.set_attribute("resolution", "llm_character")
                    chat_span.set_attribute("tool_call_rounds", str(i))
                    chat_span.set_attribute("total_tool_calls", str(total_tool_calls))
                    return final_content

                # 有工具调用 —— 记录思考过程（如果有Content）和工具调用
                self.logger.log_agent_response(msg.content, tool_calls=tool_calls_data)

                self.messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    # 判断是 MCP 还是 Legacy 工具
                    tool_type = "MCP" if tool_name.startswith("mcp_") else "Legacy"
                    print(f"  [Tool-{tool_type}] 调用工具: {tool_name}({json.dumps(args, ensure_ascii=False)[:100]}...)")
                    
                    with TracingSpan("tool_execution", {
                        "tool.name": tool_name,
                        "tool.type": tool_type,
                        "tool.arguments": json.dumps(args, ensure_ascii=False)[:500],
                    }) as tool_span:
                        result = self._execute_tool(tool_name, args)  # 使用路由器
                        tool_span.set_attribute("tool.result_length", len(result))
                    
                    print(f"  [Result] 返回: {result[:200]}{'...' if len(result) > 200 else ''}")
                    
                    # 记录工具执行结果
                    self.logger.log_tool_execution(tool_name, args, result)
                    total_tool_calls += 1

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

            # 超过最大轮次 (理论上不应该到这里，因为最后一次强制 none)
            # 但为了保险起见，还是保留一个 fallback
            error_msg = "（已达到最大工具调用轮次，无法生成回答）"
            self.logger.log_error(error_msg)
            chat_span.set_attribute("resolution", "max_rounds_exceeded")
            return error_msg

    def reset(self):
        """重置对话（保留 system prompt）"""
        self._init_system_prompt()
        print("对话已重置。")
    
    def cleanup(self):
        """清理资源（用于显式释放）"""
        if self.mcp_client:
            try:
                self.mcp_client.cleanup()
                logger.info("[Agent] MCP 客户端已清理")
            except Exception as e:
                logger.exception("[Agent] MCP 客户端清理失败: %s", e)
    
    def __del__(self):
        """析构函数：确保资源释放"""
        self.cleanup()
