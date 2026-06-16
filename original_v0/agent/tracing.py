# -*- coding: utf-8 -*-
"""
Phoenix AI 可观测性集成模块

支持两种安装方式：
  方式 A（完整版，本地 Web UI）:
    pip install arize-phoenix openinference-instrumentation-openai
  方式 B（轻量版，连接远程或 Docker 部署的 Phoenix）:
    pip install arize-phoenix-otel openinference-instrumentation-openai

如果都未安装，则 graceful fallback，不影响 Agent 运行。
"""

# 抑制 Phoenix 内部的已知无害警告
import warnings
import logging
warnings.filterwarnings("ignore", message=".*non-serializable-default.*")
warnings.filterwarnings("ignore", message=".*Skipped unsupported reflection.*")
logger = logging.getLogger(__name__)

# 全局状态
PHOENIX_ENABLED = False
_tracer = None


def setup_tracing():
    """
    初始化 Phoenix tracing。
    如果 Phoenix 未安装，graceful fallback，不影响 Agent 运行。
    """
    global PHOENIX_ENABLED, _tracer

    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
        from opentelemetry import trace
    except ImportError:
        logger.info("Phoenix 依赖未安装，跳过可观测性初始化")
        logger.info("可通过以下命令安装: pip install arize-phoenix openinference-instrumentation-openai")
        return

    # 尝试方式 A：完整版 arize-phoenix（本地 Web UI）
    try:
        import phoenix as px
        from phoenix.otel import register

        px.launch_app()

        tracer_provider = register(
            project_name="招商经理Agent",
            auto_instrument=False,
        )

        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        _tracer = trace.get_tracer("recruitment-agent")

        PHOENIX_ENABLED = True
        logger.info("=" * 50)
        logger.info("Phoenix AI 可观测性已启动（本地模式）")
        logger.info("Web UI: http://localhost:6006")
        logger.info("=" * 50)
        return

    except ImportError:
        pass  # 完整版未安装，尝试轻量版
    except Exception as e:
        logger.warning("Phoenix 完整版启动失败: %s", e)

    # 尝试方式 B：轻量版 arize-phoenix-otel（连接远程 Phoenix）
    try:
        from phoenix.otel import register

        tracer_provider = register(
            project_name="招商经理Agent",
            auto_instrument=False,
        )

        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        _tracer = trace.get_tracer("recruitment-agent")

        PHOENIX_ENABLED = True
        logger.info("=" * 50)
        logger.info("Phoenix AI 可观测性已启动（远程模式）")
        logger.info("请确保 Phoenix Server 已运行")
        logger.info("=" * 50)
        return

    except ImportError:
        logger.info("phoenix-otel 未安装，跳过可观测性初始化")
    except Exception as e:
        logger.warning("Phoenix 初始化失败: %s", e)
        logger.info("Agent 将正常运行，但不会记录追踪数据")


def get_tracer():
    """获取 OpenTelemetry tracer，用于创建自定义 span"""
    return _tracer


class TracingSpan:
    """
    上下文管理器：创建自定义追踪 span。
    如果 Phoenix 未启用，则为空操作 (no-op)。

    用法:
        with TracingSpan("tool_execution", {"tool.name": "xxx"}) as span:
            result = execute_tool(...)
            span.set_attribute("tool.result_length", len(result))
    """

    def __init__(self, name: str, attributes: dict = None):
        self.name = name
        self.attributes = attributes or {}
        self.span = None

    def __enter__(self):
        if PHOENIX_ENABLED and _tracer:
            self.span = _tracer.start_span(self.name)
            for k, v in self.attributes.items():
                self.span.set_attribute(k, str(v))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_type:
                self.span.set_attribute("error", True)
                self.span.set_attribute("error.message", str(exc_val))
            self.span.end()
        return False  # 不吞异常

    def set_attribute(self, key: str, value):
        """在 span 上设置额外属性"""
        if self.span:
            self.span.set_attribute(key, str(value))
