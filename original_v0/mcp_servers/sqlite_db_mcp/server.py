# -*- coding: utf-8 -*-
"""
SQLite Database MCP Server
--------------------------
提供对园区招商数据库的 MCP 标准访问接口

包含工具:
- search_enterprises: 搜索企业
- search_park_resources: 搜索园区资源
- query_policies: 查询政策
- query_crm_status: 查询CRM状态
"""
import sqlite3
import json
import os
import sys
from typing import Any

# 使用 mcp 库
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 数据库路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "db", "park_data.db")

# 创建 MCP 服务器实例
server = Server("sqlite-database-server")


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="search_enterprises",
            description="从OPC企业池（招商候选目标库）中检索潜在招商目标企业。注意：这里搜索的是候选目标企业，不是已入驻的企业。查已入驻企业请用query_crm_status。",
            inputSchema={
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "行业关键词，如'半导体'、'人工智能'、'生物医药'"
                    },
                    "min_employees": {
                        "type": "integer",
                        "description": "最小员工数"
                    },
                    "max_employees": {
                        "type": "integer",
                        "description": "最大员工数"
                    },
                    "financing_stage": {
                        "type": "string",
                        "description": "融资阶段：'天使轮','A轮','B轮','C轮','D轮','Pre-IPO','已上市'"
                    },
                    "region": {
                        "type": "string",
                        "description": "企业所在区域，如'武汉','深圳','北京'"
                    },
                },
            },
        ),
        Tool(
            name="search_park_resources",
            description="查询园区可用的办公室、厂房、实验室等资源。",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "enum": ["office", "factory", "lab", "all"],
                        "description": "资源类型"
                    },
                    "min_area": {
                        "type": "number",
                        "description": "最小面积（平方米）"
                    },
                    "max_rent": {
                        "type": "number",
                        "description": "最高租金（元/平方米/月）"
                    },
                },
            },
        ),
        Tool(
            name="query_policies",
            description="查询园区优惠政策信息。",
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_type": {
                        "type": "string",
                        "description": "政策类型（可选）"
                    },
                },
            },
        ),
        Tool(
            name="query_crm_status",
            description="查询CRM客户跟进状态，包括联系人、阶段、上次沟通记录。",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "企业名称（支持模糊匹配）"
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["初步接触", "洽谈中", "意向明确", "已签约", "已流失", "all"],
                        "description": "跟进阶段筛选"
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
        if name == "search_enterprises":
            result = search_enterprises(**arguments)
        elif name == "search_park_resources":
            result = search_park_resources(**arguments)
        elif name == "query_policies":
            result = query_policies(**arguments)
        elif name == "query_crm_status":
            result = query_crm_status(**arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False))]
        
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"工具执行出错: {str(e)}"}, ensure_ascii=False)
        )]


# ========== 工具实现 ==========

def search_enterprises(industry=None, min_employees=None, max_employees=None,
                      financing_stage=None, region=None, **kwargs):
    """搜索企业"""
    conn = get_db()
    sql = "SELECT * FROM enterprises WHERE 1=1"
    params = []
    
    if industry:
        sql += " AND (industry LIKE ? OR sub_industry LIKE ?)"
        params += [f"%{industry}%", f"%{industry}%"]
    if min_employees:
        sql += " AND employees >= ?"
        params.append(int(min_employees))
    if max_employees:
        sql += " AND employees <= ?"
        params.append(int(max_employees))
    if financing_stage:
        sql += " AND financing_stage = ?"
        params.append(financing_stage)
    if region:
        sql += " AND region LIKE ?"
        params.append(f"%{region}%")
    
    # 先查总数
    count_sql = sql.replace("SELECT *", "SELECT COUNT(*)")
    total_count = conn.execute(count_sql, params).fetchone()[0]
    
    sql += " LIMIT 20"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    results = [dict(r) for r in rows]
    return json.dumps({"count": len(results), "total_in_pool": total_count, "enterprises": results, "note": f"显示前{len(results)}条，企业池共{total_count}家"}, ensure_ascii=False)


def search_park_resources(resource_type=None, min_area=None, max_rent=None, **kwargs):
    """搜索园区资源"""
    conn = get_db()
    sql = "SELECT * FROM park_resources WHERE 1=1"
    params = []
    
    if resource_type and resource_type != "all":
        sql += " AND type = ?"
        params.append(resource_type)
    if min_area:
        sql += " AND area_sqm >= ?"
        params.append(float(min_area))
    if max_rent:
        sql += " AND rent_per_sqm <= ?"
        params.append(float(max_rent))
    
    rows = conn.execute(sql, params).fetchall()
    
    # 同时查询政策
    policies = conn.execute("SELECT * FROM park_policies").fetchall()
    conn.close()
    
    result = {
        "resources": [dict(r) for r in rows],
        "count": len(rows),
        "policies": [dict(p) for p in policies]
    }
    return json.dumps(result, ensure_ascii=False)


def query_policies(policy_type=None, **kwargs):
    """查询政策"""
    conn = get_db()
    sql = "SELECT * FROM park_policies WHERE 1=1"
    params = []
    
    if policy_type:
        sql += " AND type LIKE ?"
        params.append(f"%{policy_type}%")
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    return json.dumps({"policies": [dict(r) for r in rows]}, ensure_ascii=False)


def query_crm_status(company_name=None, stage=None, **kwargs):
    """查询CRM状态"""
    conn = get_db()
    sql = "SELECT * FROM crm_records WHERE 1=1"
    params = []
    
    if company_name:
        sql += " AND company_name LIKE ?"
        params.append(f"%{company_name}%")
    if stage and stage != "all":
        sql += " AND stage = ?"
        params.append(stage)
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    results = [dict(r) for r in rows]
    if not results:
        return json.dumps({
            "found": False,
            "message": f"CRM中未找到'{company_name or ''}'的记录"
        }, ensure_ascii=False)
    
    return json.dumps({"found": True, "records": results}, ensure_ascii=False)


# ========== 启动服务器 ==========

async def main():
    """启动 MCP 服务器"""
    # 使用 stdio 模式运行
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream, 
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
