# -*- coding: utf-8 -*-
"""
Industry Graph MCP Server
--------------------------
提供对产业图谱的 MCP 访问接口

包含工具:
- query_industry_chain: 查询产业链关系
- find_related_companies: 查找相关企业
- analyze_ecosystem: 分析产业生态
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
GRAPH_FILE = os.path.join(PROJECT_ROOT, "db", "industry_graph.json")

# 创建 MCP 服务器实例
server = Server("industry-graph-server")


def load_graph_data() -> dict:
    """加载产业图谱数据"""
    if not os.path.exists(GRAPH_FILE):
        return {"nodes": [], "edges": []}
    
    try:
        with open(GRAPH_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"读取图谱数据失败: {str(e)}"}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="query_industry_chain",
            description="查询产业链上下游关系",
            inputSchema={
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "产业名称"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "查询深度（默认1层）",
                        "default": 1
                    },
                },
                "required": ["industry"]
            },
        ),
        Tool(
            name="find_related_companies",
            description="根据产业关系查找相关企业",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "企业名称"
                    },
                    "relation_type": {
                        "type": "string",
                        "enum": ["upstream", "downstream", "competitor", "partner", "all"],
                        "description": "关系类型"
                    },
                },
                "required": ["company_name"]
            },
        ),
        Tool(
            name="analyze_ecosystem",
            description="分析产业生态的完整性和集聚度",
            inputSchema={
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "产业名称"
                    },
                },
                "required": ["industry"]
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """调用工具"""
    try:
        arguments = arguments or {}
        if name == "query_industry_chain":
            result = query_industry_chain(**arguments)
        elif name == "find_related_companies":
            result = find_related_companies(**arguments)
        elif name == "analyze_ecosystem":
            result = analyze_ecosystem(**arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False))]
        
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"工具执行出错: {str(e)}"}, ensure_ascii=False)
        )]


# ========== 工具实现 ==========

def query_industry_chain(industry: str, depth: int = 1, **kwargs):
    """查询产业链"""
    data = load_graph_data()
    
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)
    
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    
    # 查找匹配的产业节点
    target_nodes = [n for n in nodes if industry.lower() in n.get("name", "").lower()]
    
    if not target_nodes:
        return json.dumps({
            "found": False,
            "message": f"未找到产业'{industry}'的图谱数据"
        }, ensure_ascii=False)
    
    # 构建产业链（简化版：只查找直接关联）
    result_nodes = target_nodes[:]
    result_edges = []
    
    for node in target_nodes:
        node_id = node.get("id")
        # 查找相关边
        related_edges = [e for e in edges if e.get("source") == node_id or e.get("target") == node_id]
        result_edges.extend(related_edges)
        
        # 添加相关节点
        for edge in related_edges:
            related_node_id = edge.get("target") if edge.get("source") == node_id else edge.get("source")
            related_node = next((n for n in nodes if n.get("id") == related_node_id), None)
            if related_node and related_node not in result_nodes:
                result_nodes.append(related_node)
    
    return json.dumps({
        "found": True,
        "industry": industry,
        "nodes": result_nodes,
        "edges": result_edges,
        "summary": f"找到 {len(result_nodes)} 个相关产业节点，{len(result_edges)} 条产业链关系"
    }, ensure_ascii=False)


def find_related_companies(company_name: str, relation_type: str = "all", **kwargs):
    """查找相关企业"""
    data = load_graph_data()
    
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)
    
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    
    # 查找企业节点
    company_nodes = [n for n in nodes if n.get("type") == "company" and 
                     company_name.lower() in n.get("name", "").lower()]
    
    if not company_nodes:
        return json.dumps({
            "found": False,
            "message": f"未找到企业'{company_name}'的图谱数据"
        }, ensure_ascii=False)
    
    company_node = company_nodes[0]
    company_id = company_node.get("id")
    
    # 查找关系
    related = []
    for edge in edges:
        if edge.get("source") == company_id or edge.get("target") == company_id:
            if relation_type != "all" and edge.get("relation") != relation_type:
                continue
            
            # 找到对方节点
            other_id = edge.get("target") if edge.get("source") == company_id else edge.get("source")
            other_node = next((n for n in nodes if n.get("id") == other_id), None)
            
            if other_node:
                related.append({
                    "company": other_node.get("name"),
                    "relation": edge.get("relation"),
                    "industry": other_node.get("industry", "")
                })
    
    return json.dumps({
        "found": True,
        "company": company_node.get("name"),
        "related_companies": related,
        "count": len(related)
    }, ensure_ascii=False)


def analyze_ecosystem(industry: str, **kwargs):
    """分析产业生态"""
    data = load_graph_data()
    
    if "error" in data:
        return json.dumps(data, ensure_ascii=False)
    
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    
    # 统计产业相关企业数量
    industry_nodes = [n for n in nodes if industry.lower() in n.get("industry", "").lower()]
    
    # 统计关系类型
    relation_stats = {}
    for edge in edges:
        rel_type = edge.get("relation", "unknown")
        relation_stats[rel_type] = relation_stats.get(rel_type, 0) + 1
    
    # 简单评分
    completeness_score = min(len(industry_nodes) * 10, 100)  # 企业数量评分
    
    return json.dumps({
        "industry": industry,
        "companies_count": len(industry_nodes),
        "relations_count": len(edges),
        "relation_types": relation_stats,
        "completeness_score": completeness_score,
        "analysis": f"该产业在园区生态中有 {len(industry_nodes)} 家相关企业，产业链完整度评分 {completeness_score}/100"
    }, ensure_ascii=False)


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
