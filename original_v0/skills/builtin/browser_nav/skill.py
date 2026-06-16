# -*- coding: utf-8 -*-
"""
Browser Navigation Skill
利用浏览器 MCP 进行网页导航（不处理搜索）
"""
import json
import logging
from typing import Dict, Any, List

# 尝试导入 BaseSkill，处理可能的路径问题
try:
    from skills.base_skill import BaseSkill
except ImportError:
    #如果在 plugins 目录下运行
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)

class BrowserNavSkill(BaseSkill):
    """
    浏览器导航技能
    允许用户通过自然语言控制浏览器 MCP 进行网页访问和浏览
    """
    
    def can_handle(self, context: Dict[str, Any]) -> bool:
        """
        判断是否触发该技能
        触发词：打开、浏览、访问、open、browse、visit
        """
        user_input = context.get("user_input", "")
        keywords = ["打开", "浏览", "访问", "open", "browse", "visit"]
        return self._match_keywords(user_input, keywords)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技能逻辑
        """
        user_input = context.get("user_input", "")
        mcp_client = context.get("mcp_client")
        
        if not mcp_client:
            return {
                "handled": True,
                "response": "⚠️ 未检测到 MCP 客户端，无法使用浏览器自动化功能。请检查配置。"
            }
        
        # 1. 获取可用工具
        # 注意：这里使用的是同步 wrapper
        try:
            all_tools = mcp_client.get_all_tools()
        except Exception as e:
            return {
                "handled": True,
                "response": f"⚠️ 获取工具列表失败: {e}"
            }

        # 2. 查找浏览器相关工具（优先 Playwright，兼容 BrowserOS）
        browser_tools = [
            t for t in all_tools
            if (
                "mcp_playwright_" in t["function"]["name"]
                or "mcp_browseros_" in t["function"]["name"]
                or "_browser_" in t["function"]["name"]
            )
        ]
        
        if not browser_tools:
            return {
                "handled": True,
                "response": (
                    "⚠️ 未检测到可用的浏览器 MCP 工具。\n"
                    "请检查 Playwright MCP 是否已启用；若使用 BrowserOS，请确认 BROWSEROS_MCP_URL 可用。"
                )
            }

        # 3. 简单的意图识别与工具映射 (Heuristic)
        # 这里只是一个简单的演示，实际可能需要交给 LLM 决策，但 Skill 的初衷是快速路径
        
        target_tool = None
        args = {}
        
        # 查找特定功能的工具名称
        def find_tool_by_keyword(keyword):
            for t in browser_tools:
                name = t["function"]["name"].lower()
                if keyword in name:
                    return t["function"]["name"]
            return None

        # [Intent: Navigate/Open]
        if any(k in user_input.lower() for k in ["打开", "访问", "open", "visit"]):
            url = user_input
            for k in ["打开", "访问", "open", "visit", "url", "the"]:
                url = url.replace(k, "").strip()
            
            # 尝试寻找 navigate/goto 工具
            tool_name = find_tool_by_keyword("navigate") or find_tool_by_keyword("goto") or find_tool_by_keyword("open")
            if tool_name:
                target_tool = tool_name
                args = {"url": url}
        
        # 如果没有明确匹配到快速路径，或者没找到工具
        if not target_tool:
             # 返回 handled=False 让主 Loop 的 LLM 去处理（它可以更灵活地调用工具）
             logger.info("[BrowserSkill] 未匹配到特定快捷指令，转交 LLM 处理")
             return {"handled": False}
        
        # 4. 执行工具
        logger.info(f"[BrowserSkill] 直接调用工具: {target_tool} args={args}")
        try:
            result = mcp_client.call_tool(target_tool, args)
            return {
                "handled": True,
                "response": f"✅ 已通过浏览器 MCP 执行操作。\n\n**结果反馈**:\n{result}"
            }
        except Exception as e:
             return {
                "handled": True,
                "response": f"❌ 调用浏览器 MCP 工具失败: {e}"
            }
