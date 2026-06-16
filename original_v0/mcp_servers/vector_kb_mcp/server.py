# -*- coding: utf-8 -*-
"""
Vector Knowledge MCP Server
----------------------------
提供对向量知识库的 MCP 访问接口（使用 ChromaDB）

包含工具:
- semantic_search: 语义搜索
- find_similar_cases: 查找相似案例
- query_knowledge: 知识查询
"""
import json
import os
import sys
import logging
from typing import Any, List, Dict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 数据路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 创建 MCP 服务器实例
server = Server("vector-knowledge-server")
logger = logging.getLogger(__name__)

# 全局变量存储 ChromaDB 实例
_vector_store = None

# Pre-import to avoid threading deadlocks with numpy/MKL in subprocess
try:
    logger.debug("[VectorMCP] Pre-loading chromadb...")
    from data.init_chromadb import get_vector_store as get_singleton
    # Configure env vars are set in init_chromadb on import
except Exception as e:
    logger.exception("[VectorMCP] Pre-load failed: %s", e)


def get_vector_store():
    """获取或创建 ChromaDB 向量存储实例"""
    global _vector_store, get_singleton
    # print(f"[VectorMCP-Debug] get_vector_store called. Current instance: {_vector_store}", file=sys.stderr)
    if _vector_store is None:
        try:
            # 确保 get_singleton 可用
            if 'get_singleton' not in globals():
                logger.debug("[VectorMCP] importing get_vector_store lazily...")
                from data.init_chromadb import get_vector_store as get_singleton

            # print("[VectorMCP-Debug] Calling get_singleton()...", file=sys.stderr)
            _vector_store = get_singleton()  # 使用单例模式
            # print("[VectorMCP-Debug] Singleton created.", file=sys.stderr)
        except Exception as e:
            logger.exception("[VectorMCP] 初始化 ChromaDB 失败: %s", e)
            return None
    return _vector_store


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="semantic_search",
            description="在知识库中进行语义搜索",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询文本"
                    },
                    "collection": {
                        "type": "string",
                        "description": "Collection名称，all表示搜索所有集合",
                        "default": "all"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量（默认5）",
                        "default": 5
                    },
                },
                "required": ["query"]
            },
        ),
        Tool(
            name="find_similar_cases",
            description="查找相似的招商案例",
            inputSchema={
                "type": "object",
                "properties": {
                    "case_description": {
                        "type": "string",
                        "description": "案例描述"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "结果数量限制",
                        "default": 3
                    },
                },
                "required": ["case_description"]
            },
        ),
        Tool(
            name="query_knowledge",
            description="查询知识库中的特定知识条目",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "知识主题"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["policy", "case", "faq", "guide", "all"],
                        "description": "知识类别",
                        "default": "all"
                    },
                "top_k": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5
                    },
                },
                "required": ["topic"]
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """调用工具"""
    try:
        arguments = arguments or {}
        if name == "semantic_search":
            result = semantic_search(**arguments)
        elif name == "find_similar_cases":
            result = find_similar_cases(**arguments)
        elif name == "query_knowledge":
            result = query_knowledge(**arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False))]
        
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"工具执行出错: {str(e)}"}, ensure_ascii=False)
        )]


# ========== 工具实现 ==========

def semantic_search(query: str, collection: str = "all", top_k: int = 5, **kwargs):
    """语义搜索"""
    logger.debug("[VectorMCP] semantic_search called")
    try:
        store = get_vector_store()
    except Exception as e:
        logger.exception("[VectorMCP] get_vector_store failed: %s", e)
        return json.dumps({"error": f"Store Init Failed: {e}"}, ensure_ascii=False)

    logger.debug("[VectorMCP] store obtained: %s", bool(store))

    if store is None:
        return json.dumps({"error": "向量存储未初始化"}, ensure_ascii=False)
    
    try:
        top_k = max(1, int(top_k))
        logger.debug("[VectorMCP] calling store.query")
        results = store.query(query, collection=collection, top_k=top_k)
        logger.debug("[VectorMCP] store.query returned %d results", len(results))
        
        if not results:
            return json.dumps({
                "found": False,
                "message": "未找到相关结果"
            }, ensure_ascii=False)
        
        return json.dumps({
            "query": query,
            "found": True,
            "count": len(results),
            "results": results
        }, ensure_ascii=False)
    
    except (ValueError, RuntimeError, ConnectionError) as e:
        # 捕获特定的向量存储错误
        return json.dumps({"error": f"搜索失败: {str(e)}"}, ensure_ascii=False)


def find_similar_cases(case_description: str, limit: int = 3, **kwargs):
    """查找相似案例"""
    store = get_vector_store()
    if store is None:
        return json.dumps({"error": "向量存储未初始化"}, ensure_ascii=False)
    
    try:
        # 从 company_profiles collection 中搜索（这里存储了案例）
        limit = max(1, int(limit))
        all_results = store.query(case_description, collection="all", top_k=limit * 2)
        
        # 过滤出案例类型的文档
        case_results = [
            r for r in all_results 
            if (r.get("metadata") or {}).get("type") == "case"
        ][:limit]
        
        if not case_results:
            return json.dumps({
                "found": False,
                "message": "知识库中暂无招商案例数据"
            }, ensure_ascii=False)
        
        # 格式化结果
        formatted_cases = []
        for result in case_results:
            metadata = result.get("metadata") or {}
            formatted_cases.append({
                "id": result.get("id", ""),
                "collection": result.get("collection", ""),
                "title": metadata.get("title", "未命名案例"),
                "content": result["content"],
                "company": metadata.get("company", ""),
                "industry": metadata.get("industry", ""),
                "similarity": result["similarity"],
                "citation": {
                    "id": result.get("id", ""),
                    "collection": result.get("collection", ""),
                    "title": metadata.get("title", ""),
                    "type": metadata.get("type", ""),
                }
            })
        
        return json.dumps({
            "description": case_description,
            "found": True,
            "count": len(formatted_cases),
            "similar_cases": formatted_cases
        }, ensure_ascii=False)
    
    except (ValueError, RuntimeError, ConnectionError) as e:
        # 捕获特定的向量存储错误
        return json.dumps({"error": f"查找案例失败: {str(e)}"}, ensure_ascii=False)


def query_knowledge(topic: str, category: str = "all", top_k: int = 5, **kwargs):
    """查询知识"""
    store = get_vector_store()
    if store is None:
        return json.dumps({"error": "向量存储未初始化"}, ensure_ascii=False)
    
    try:
        # 从所有 collection 中搜索
        top_k = max(1, int(top_k))
        all_results = store.query(topic, collection="all", top_k=top_k * 2)
        
        # 根据类别过滤
        filtered_results = []
        for result in all_results:
            metadata = result.get("metadata") or {}
            doc_type = metadata.get("type", "")
            if category == "all" or doc_type == category:
                filtered_results.append({
                    "id": result.get("id", ""),
                    "collection": result.get("collection", ""),
                    "title": metadata.get("title", ""),
                    "type": doc_type,
                    "content": result["content"],
                    "metadata": metadata,
                    "similarity": result["similarity"],
                    "citation": {
                        "id": result.get("id", ""),
                        "collection": result.get("collection", ""),
                        "title": metadata.get("title", ""),
                        "type": doc_type,
                    }
                })
        
        # 限制返回数量
        filtered_results = filtered_results[:top_k]
        
        return json.dumps({
            "topic": topic,
            "category": category,
            "found": len(filtered_results) > 0,
            "count": len(filtered_results),
            "knowledge": filtered_results
        }, ensure_ascii=False)
    
    except (ValueError, RuntimeError, ConnectionError) as e:
        # 捕获特定的向量存储错误
        return json.dumps({"error": f"查询知识失败: {str(e)}"}, ensure_ascii=False)


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
