# -*- coding: utf-8 -*-
"""Stable tool executor used by the Agent loop."""
import logging

from tools.implementations import TOOL_REGISTRY
from tools.response_utils import tool_error

logger = logging.getLogger(__name__)


def execute_tool(name: str, arguments: dict) -> str:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return tool_error("UNKNOWN_TOOL", f"Unknown tool: {name}", source="legacy", tool=name)

    try:
        return fn(**(arguments or {}))
    except Exception as e:
        logger.exception("Legacy tool execution failed: %s", name)
        return tool_error(
            "LEGACY_TOOL_ERROR",
            f"Tool execution failed: {str(e)}",
            source="legacy",
            tool=name,
        )
