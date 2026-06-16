# -*- coding: utf-8 -*-
"""
招商经理 Agent MVP — CLI 入口
用法:
  python main.py
"""
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(__file__))
logger = logging.getLogger(__name__)

# 解决 Windows 下打印 emoji 报错的问题
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')


def configure_logging():
    """初始化全局日志配置（可通过 LOG_LEVEL 覆盖级别）"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level, logging.INFO)
    project_root = os.path.dirname(__file__)
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    app_log_path = os.path.join(log_dir, "app.log")

    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        app_log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[console_handler, file_handler],
    )


def init_all_databases():
    """初始化所有数据库"""
    print("=" * 50)
    print("初始化数据库...")
    print("=" * 50)

    print("\n[1/3] 初始化 SQLite 数据库...")
    from data.init_sqlite import init_db
    init_db()

    print("\n[2/3] 初始化 NetworkX 产业链图谱...")
    from data.init_graph import init_graph
    init_graph()

    print("\n[3/3] 初始化向量知识库...")
    from data.init_chromadb import init_vector_store
    init_vector_store()
    
    # 释放向量库实例，避免文件锁冲突（因为 Agent 在子进程中会重新初始化）
    try:
        from data.init_chromadb import reset_vector_store
        reset_vector_store()
    except Exception as e:
        logger.warning("重置向量库实例失败: %s", e)

    print("\n" + "=" * 50)
    print("所有数据库初始化完成！")
    print("=" * 50)


def run_chat():
    """启动交互式对话"""
    # 初始化 Phoenix 可观测性
    from agent.tracing import setup_tracing
    setup_tracing()

    from agent.agent_loop import RecruitmentAgent

    print("=" * 50)
    print("🏢 光谷智创园 · 招商经理 Agent (MVP)")
    print("=" * 50)
    print("输入你的问题，输入 'quit' 退出，输入 'reset' 重置对话\n")

    agent = RecruitmentAgent()

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        if user_input.lower() == "reset":
            agent.reset()
            continue

        print()  # 空行
        try:
            print("招商经理", end="", flush=True)
            streamed_parts = []
            stream_mode_announced = False

            def _on_stream_chunk(chunk: str):
                nonlocal stream_mode_announced
                if not stream_mode_announced:
                    print("[STREAM]: ", end="", flush=True)
                    stream_mode_announced = True
                streamed_parts.append(chunk)
                print(chunk, end="", flush=True)

            reply = agent.chat(
                user_input,
                on_stream_chunk=_on_stream_chunk,
            )
            # 非流式路径（如 Skill 直接 handled）需要补打完整回复
            if not streamed_parts:
                if reply:
                    print(f"[NON-STREAM]: {reply}", end="", flush=True)
                else:
                    print("[NON-STREAM]: （模型未返回文本）", end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"\n错误: {e}\n")


if __name__ == "__main__":
    # 默认使用免费 Playwright MCP（无需 API Key）
    if os.environ.get("ENABLE_PLAYWRIGHT_MCP", "1").lower() in ("0", "false", "no", "off"):
        print("提示: 当前已禁用 Playwright MCP（ENABLE_PLAYWRIGHT_MCP=0）。")

    configure_logging()
    # 始终先初始化数据库，再启动对话
    init_all_databases()
    print()
    run_chat()
