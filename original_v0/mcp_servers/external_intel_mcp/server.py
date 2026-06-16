# -*- coding: utf-8 -*-
"""
External Intelligence MCP Server
---------------------------------
提供对外部情报 JSON 数据的 MCP 访问接口

包含工具:
- query_enterprise_news: 查询企业新闻
- query_tech_trends: 查询技术趋势
- query_market_data: 查询市场数据
"""
import json
import os
import sys
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 数据路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
EXTERNAL_API_DIR = os.path.join(PROJECT_ROOT, "external_api")

# 创建 MCP 服务器实例
server = Server("external-intelligence-server")


def load_json_file(filename: str) -> dict:
    """加载 JSON 文件"""
    filepath = os.path.join(EXTERNAL_API_DIR, filename)
    if not os.path.exists(filepath):
        return {"error": f"文件不存在: {filename}"}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"读取文件失败: {str(e)}"}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="query_enterprise_news",
            description="查询企业相关的新闻和动态信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "企业名称（支持模糊匹配）"
                    },
                    "news_type": {
                        "type": "string",
                        "enum": ["融资", "业务", "荣誉", "all"],
                        "description": "新闻类型筛选"
                    },
                },
            },
        ),
        Tool(
            name="query_tech_trends",
            description="查询技术趋势和行业动态",
            inputSchema={
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "行业关键词"
                    },
                },
            },
        ),
        Tool(
            name="query_market_data",
            description="查询市场数据和竞争分析",
            inputSchema={
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "description": "行业板块"
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """调用工具"""
    try:
        arguments = arguments or {}
        if name == "query_enterprise_news":
            result = query_enterprise_news(**arguments)
        elif name == "query_tech_trends":
            result = query_tech_trends(**arguments)
        elif name == "query_market_data":
            result = query_market_data(**arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False))]
        
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"工具执行出错: {str(e)}"}, ensure_ascii=False)
        )]


# ========== 工具实现 ==========

def query_enterprise_news(company_name=None, news_type=None, **kwargs):
    """查询企业新闻"""
    data = load_json_file("enterprise_news.json")
    
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)
    
    news_list = data.get("news", [])
    results = []
    
    # 过滤
    for news in news_list:
        if company_name and company_name.lower() not in news.get("company", "").lower():
            continue
        if news_type and news_type != "all" and news.get("type") != news_type:
            continue
        results.append(news)
    
    return json.dumps({
        "count": len(results),
        "news": results
    }, ensure_ascii=False)


def query_tech_trends(industry=None, **kwargs):
    """查询技术趋势"""
    data = load_json_file("tech_trends.json")
    
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)
    
    trends = data.get("trends", [])
    results = []
    
    # 过滤
    for trend in trends:
        if industry:
            if industry.lower() in trend.get("industry", "").lower() or \
               industry.lower() in trend.get("description", "").lower():
                results.append(trend)
        else:
            results.append(trend)
    
    return json.dumps({
        "count": len(results),
        "trends": results
    }, ensure_ascii=False)


def query_market_data(sector=None, **kwargs):
    """查询市场数据"""
    data = load_json_file("market_analysis.json")
    
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)
    
    # 简单返回所有数据或按 sector 过滤
    if sector:
        markets = data.get("markets", [])
        results = [m for m in markets if sector.lower() in m.get("sector", "").lower()]
        return json.dumps({
            "count": len(results),
            "markets": results
        }, ensure_ascii=False)
    
    return json.dumps(data, ensure_ascii=False)


# ========== 启动服务器 ==========

async def main():
    """启动 MCP 服务器"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
