# -*- coding: utf-8 -*-
"""7 个 MCP 工具的实际实现 —— 从 SQLite / ChromaDB / NetworkX / JSON 读取数据"""
import sqlite3
import json
import os
import logging
from tools.response_utils import tool_error

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "park_data.db")
RISK_JSON = os.path.join(BASE_DIR, "external_api", "risk_data.json")
INTEL_JSON = os.path.join(BASE_DIR, "external_api", "company_intelligence.json")
GRAPH_JSON = os.path.join(BASE_DIR, "db", "industry_graph.json")
logger = logging.getLogger(__name__)


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── 1. search_enterprises ─────────────────────────
def search_enterprises(industry=None, min_employees=None, max_employees=None,
                       financing_stage=None, region=None, tags=None, **_):
    conn = _get_db()
    try:
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
            # 支持 "C轮以上" 这类查询
            stage_order = ["种子轮","天使轮","Pre-A轮","A轮","A+轮","B轮","B+轮","C轮","D轮","Pre-IPO","已上市"]
            stage_clean = financing_stage.replace("以上", "").replace("及以上", "").strip()
            if stage_clean in stage_order and ("以上" in financing_stage or "及以上" in financing_stage):
                idx = stage_order.index(stage_clean)
                above = stage_order[idx:]
                placeholders = ",".join(["?"] * len(above))
                sql += f" AND financing_stage IN ({placeholders})"
                params += above
            else:
                sql += " AND financing_stage = ?"
                params.append(stage_clean)
        if region:
            sql += " AND region LIKE ?"
            params.append(f"%{region}%")
        if tags:
            sql += " AND tags LIKE ?"
            params.append(f"%{tags}%")
        # 先查总数
        count_sql = sql.replace("SELECT *", "SELECT COUNT(*)")
        total_count = conn.execute(count_sql, params).fetchone()[0]
        
        sql += " LIMIT 20"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    results = [dict(r) for r in rows]
    if not results:
        return json.dumps({"count": 0, "total_in_pool": total_count, "enterprises": [], "message": "未找到匹配企业"}, ensure_ascii=False)
    return json.dumps({"count": len(results), "total_in_pool": total_count, "enterprises": results, "note": f"显示前{len(results)}条，企业池共{total_count}家"}, ensure_ascii=False)


# ── 2. get_company_risk ──────────────────────────
def get_company_risk(company_name, **_):
    """企业风险评估（6维加权评分模型）"""
    # 读取风险数据
    with open(RISK_JSON, "r", encoding="utf-8") as f:
        risk_db = json.load(f)
    
    # 精确匹配企业
    match_data = None
    for key in risk_db:
        if company_name in key or key in company_name:
            match_data = risk_db[key]
            break
    
    # 如果没有现成数据，使用智能评分模型
    if not match_data:
        # 从数据库获取企业基本信息
        conn = _get_db()
        try:
            sql = "SELECT * FROM enterprises WHERE name LIKE ? LIMIT 1"
            row = conn.execute(sql, (f"%{company_name}%",)).fetchone()
        finally:
            conn.close()
        
        if not row:
            return json.dumps({"found": False, "message": f"未找到'{company_name}'的风险数据"}, ensure_ascii=False)
        
        company_info = dict(row)
        
        # 使用6维风险评分模型
        match_data = _calculate_risk_score(company_info)
    
    return json.dumps({"found": True, **match_data}, ensure_ascii=False)


def _calculate_risk_score(company_info):
    """6维风险评分模型
    
    维度及权重：
    1. 行业风险 (25%)  - 行业政策敏感度、竞争激烈度
    2. 财务健康 (20%)  - 融资阶段、注册资本、营收能力
    3. 法律风险 (20%)  - 诉讼、违规、经营异常
    4. 团队稳定 (15%)  - 创始人背景、团队变动
    5. 技术实力 (10%)  - 专利、技术认证
    6. 市场认可 (10%)  - 投资机构质量、客户认可度
    
    风险分数: 0-100，越高风险越大
    """
    industry = company_info.get("industry", "未知")
    employees = company_info.get("employees", 0)
    registered_capital = company_info.get("registered_capital", "0")
    financing_stage = company_info.get("financing_stage", "")
    established = company_info.get("established", "2020")
    tags = company_info.get("tags", "")
    
    # 1. 行业风险评分 (0-100)
    industry_risk_map = {
        "人工智能": 20, "半导体": 25, "生物医药": 30,
        "金融科技": 40, "新能源": 22, "网络安全": 18,
        "量子科技": 35, "元宇宙": 45, "区块链": 50,
        "碳中和": 25, "光通信": 20, "智能制造": 22
    }
    industry_risk = 30  # 默认值
    for key, value in industry_risk_map.items():
        if key in industry:
            industry_risk = value
            break
    
    # 2. 财务健康评分 (0-100)
    financial_health = 50  # 基础分
    
    # 融资阶段影响（早期高风险）
    stage_scores = {
        "天使轮": 50, "Pre-A": 45, "A轮": 35, "B轮": 25,
        "C轮": 18, "D轮": 12, "Pre-IPO": 8, "已上市": 5
    }
    for stage, score in stage_scores.items():
        if stage in financing_stage:
            financial_health = score
            break
    
    # 员工规模影响
    if employees < 10:
        financial_health += 15
    elif employees < 50:
        financial_health += 8
    elif employees > 200:
        financial_health -= 10
    
    # 注册资本影响
    try:
        capital_num = float(''.join(filter(str.isdigit, str(registered_capital))))
        if capital_num < 1000:
            financial_health += 10
        elif capital_num > 10000:
            financial_health -= 8
    except Exception as e:
        logger.debug("Failed to parse registered_capital for risk scoring: %s", e)
    
    financial_health = max(0, min(100, financial_health))
    
    # 3. 法律风险评分 (0-100)
    # 基于企业年龄、规模、行业等推断
    import datetime
    current_year = datetime.datetime.now().year
    try:
        founded_year = int(established[:4])
        company_age = current_year - founded_year
    except Exception:
        company_age = 3
    
    legal_risk = 15  # 基础分
    # 年轻公司法律风险较高（合同/知识产权纠纷多发）
    if company_age < 2:
        legal_risk += 20
    elif company_age < 5:
        legal_risk += 10
    else:
        legal_risk -= 5
    # 小团队法律治理通常不完善
    if employees < 20:
        legal_risk += 10
    elif employees > 100:
        legal_risk -= 5
    # 有资质认证的企业法律风险较低
    if "专精特新" in tags or "国家高新" in tags:
        legal_risk -= 10
    # 部分行业法律/合规风险较高
    high_legal_industries = ["金融科技", "区块链", "元宇宙", "生物医药"]
    for hi in high_legal_industries:
        if hi in industry:
            legal_risk += 8
            break
    legal_risk = max(0, min(100, legal_risk))
    
    # 4. 团队稳定性评分 (0-100)
    import datetime
    current_year = datetime.datetime.now().year
    try:
        founded_year = int(established[:4])
        age = current_year - founded_year
        # 公司越年轻，团队风险越高
        team_stability = max(5, 40 - age * 3)
    except Exception as e:
        logger.debug("Failed to parse established year for team_stability: %s", e)
        team_stability = 30
    
    team_stability = max(0, min(100, team_stability))
    
    # 5. 技术实力评分 (0-100，反向：越低越好)
    tech_strength = 30  # 默认
    if "专精特新" in tags or "国家高新" in tags:
        tech_strength = 10
    if "科技" in industry or "智能" in industry:
        tech_strength -= 5
    tech_strength = max(0, min(100, tech_strength))
    
    # 6. 市场认可度评分 (0-100，反向：越低越好)
    market_recognition = 40  # 默认
    if financing_stage in ["C轮", "D轮", "Pre-IPO", "已上市"]:
        market_recognition = 15
    elif financing_stage in ["A轮", "B轮"]:
        market_recognition = 28
    market_recognition = max(0, min(100, market_recognition))
    
    # 加权计算总分
    weights = {
        "industry_risk": 0.25,
        "financial_health": 0.20,
        "legal_risk": 0.20,
        "team_stability": 0.15,
        "tech_strength": 0.10,
        "market_recognition": 0.10
    }
    
    total_score = (
        industry_risk * weights["industry_risk"] +
        financial_health * weights["financial_health"] +
        legal_risk * weights["legal_risk"] +
        team_stability * weights["team_stability"] +
        tech_strength * weights["tech_strength"] +
        market_recognition * weights["market_recognition"]
    )
    
    total_score = min(100, max(0, total_score))
    
    # 风险等级判定
    if total_score < 30:
        risk_level = "低风险"
        risk_tags = []
    elif total_score < 60:
        risk_level = "中等风险"
        risk_tags = ["需关注"]
    elif total_score < 80:
        risk_level = "较高风险"
        risk_tags = ["需重点关注"]
    else:
        risk_level = "高风险"
        risk_tags = ["不建议合作"]
    
    return {
        "risk_score": round(total_score, 1),
        "risk_level": risk_level,
        "risk_tags": risk_tags,
        "risk_factors": {
            "industry_risk": round(industry_risk, 1),
            "financial_health": round(financial_health, 1),
            "legal_risk": round(legal_risk, 1),
            "team_stability": round(team_stability, 1),
            "tech_strength": round(tech_strength, 1),
            "market_recognition": round(market_recognition, 1)
        },
        "lawsuits": [],
        "negative_news": [],
        "administrative_penalty": [],
        "operating_status": "正常",
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d")
    }


# ── 3. get_industry_chain ──────────────────────────
def get_industry_chain(industry, query_type="full_chain", **_):
    import networkx as nx
    with open(GRAPH_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 修复1: chain_gaps 实际上在 data["graph"]["chain_gaps"] 中
    chain_gaps = data.get("graph", {}).get("chain_gaps", {})
    
    # 修复2: 兼容不同版本 NetworkX 对 links/edges 的字段名称要求
    # 无论 NX 找 edges 还是 links，都确保这两个键存在
    if "edges" in data and "links" not in data:
        data["links"] = data["edges"]
    elif "links" in data and "edges" not in data:
        data["edges"] = data["links"]
        
    G = nx.node_link_graph(data, directed=True, edges="links")

    # 找到匹配节点
    target = None
    for n in G.nodes():
        if industry in n or n in industry:
            target = n
            break
    if not target:
        return json.dumps({"found": False, "message": f"未找到'{industry}'的产业链数据"}, ensure_ascii=False)

    result = {"industry": target, "node_info": dict(G.nodes[target])}

    if query_type in ("full_chain", "upstream"):
        upstream = []
        for pred in G.predecessors(target):
            edge_data = G.edges[pred, target]
            upstream.append({"name": pred, "relation": edge_data.get("relation", "")})
        result["upstream"] = upstream

    if query_type in ("full_chain", "downstream"):
        downstream = []
        for succ in G.successors(target):
            edge_data = G.edges[target, succ]
            downstream.append({"name": succ, "relation": edge_data.get("relation", "")})
        result["downstream"] = downstream

    if query_type == "gap_analysis":
        gap_key = None
        for k in chain_gaps:
            if industry in k or k in industry:
                gap_key = k
                break
        if gap_key:
            result["gap_analysis"] = chain_gaps[gap_key]
        else:
            result["gap_analysis"] = {"message": "该行业暂无缺口分析数据"}

    return json.dumps(result, ensure_ascii=False)


# ── 4. search_park_resources ───────────────────────
def search_park_resources(resource_type=None, min_area=None, max_rent=None,
                          include_policies=None, **_):
    conn = _get_db()
    try:
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
        result = {"resources": [dict(r) for r in rows], "count": len(rows)}

        if include_policies:
            policies = conn.execute("SELECT * FROM park_policies").fetchall()
            result["policies"] = [dict(p) for p in policies]
    finally:
        conn.close()
    return json.dumps(result, ensure_ascii=False)


# ── 5. query_crm_status ───────────────────────────
def query_crm_status(company_name=None, stage=None, **_):
    conn = _get_db()
    try:
        sql = "SELECT * FROM crm_records WHERE 1=1"
        params = []
        if company_name:
            sql += " AND company_name LIKE ?"
            params.append(f"%{company_name}%")
        if stage and stage != "all":
            sql += " AND stage = ?"
            params.append(stage)
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    results = [dict(r) for r in rows]
    if not results:
        return json.dumps({"found": False, "message": f"CRM中未找到'{company_name or ''}'的记录"}, ensure_ascii=False)
    return json.dumps({"found": True, "records": results}, ensure_ascii=False)


# ── 6. search_knowledge_base ──────────────────────
def search_knowledge_base(query, collection="all", top_k=3, **_):
    """向量知识库检索（使用 ChromaDB + Qwen Embeddings）"""
    try:
        from data.init_chromadb import get_vector_store
        
        store = get_vector_store()  # 使用单例模式
        top_k = int(top_k) if top_k else 3
        
        # 使用 ChromaDB 向量检索
        results = store.query(query=query, collection=collection, top_k=top_k)
        
        # 格式化结果
        formatted_results = []
        for result in results:
            metadata = result.get("metadata") or {}
            formatted_results.append({
                "id": result.get("id", ""),
                "collection": result.get("collection", collection),
                "content": result["content"],
                "title": metadata.get("title", ""),
                "type": metadata.get("type", ""),
                "source": metadata.get("source", metadata.get("title", "")),
                "similarity": result["similarity"],
                "citation": {
                    "id": result.get("id", ""),
                    "collection": result.get("collection", collection),
                    "title": metadata.get("title", ""),
                    "type": metadata.get("type", ""),
                }
            })
        
        return json.dumps({"results": formatted_results, "count": len(formatted_results)}, ensure_ascii=False)
    
    except Exception as e:
        # 降级处理：如果向量数据库不可用，返回提示
        import traceback
        traceback.print_exc()
        return json.dumps({
            "error": "向量检索服务不可用",
            "message": str(e),
            "results": []
        }, ensure_ascii=False)






# ── 7. get_external_intelligence ──────────────────
def get_external_intelligence(company_name, info_type="all", **_):
    with open(INTEL_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 精确匹配
    match = None
    if company_name in data:
        match = data[company_name]
    else:
        for key, val in data.items():
            if company_name.replace("有限公司", "") in key:
                match = val
                break
    if not match:
        return json.dumps({"found": False, "message": f"未找到'{company_name}'的工商信息"}, ensure_ascii=False)

    if info_type == "all":
        return json.dumps({"found": True, **match}, ensure_ascii=False)
    elif info_type == "shareholders":
        return json.dumps({"found": True, "shareholders": match.get("shareholders", [])}, ensure_ascii=False)
    elif info_type == "patents":
        return json.dumps({"found": True, "patents": match.get("patents", {})}, ensure_ascii=False)
    elif info_type == "financing":
        return json.dumps({"found": True, "financing_history": match.get("financing_history", [])}, ensure_ascii=False)
    else:
        return json.dumps({"found": True, **match}, ensure_ascii=False)


# ── 8. get_current_time ───────────────────────────
def get_current_time(timezone=None, **_):
    """获取当前日期、时间、星期等信息"""
    import datetime as _dt
    try:
        if timezone and timezone != "Asia/Shanghai":
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone)
            now = _dt.datetime.now(tz)
        else:
            now = _dt.datetime.now()
            timezone = "Asia/Shanghai"
    except Exception:
        now = _dt.datetime.now()
        timezone = "Asia/Shanghai"

    weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return json.dumps({
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": weekday_map[now.weekday()],
        "datetime": now.strftime("%Y年%m月%d日 %H:%M:%S"),
        "timestamp": int(now.timestamp()),
        "timezone": timezone,
    }, ensure_ascii=False)


# ── 9. update_crm_record ──────────────────────────
def update_crm_record(company_name, new_stage=None, follow_up_note=None,
                      next_follow_up_date=None, **_):
    """更新 CRM 跟进记录"""
    import datetime as _dt
    if not company_name:
        return json.dumps({"success": False, "message": "请提供企业名称"}, ensure_ascii=False)

    conn = _get_db()
    try:
        # 先查找企业
        row = conn.execute(
            "SELECT * FROM crm_records WHERE company_name LIKE ? LIMIT 1",
            (f"%{company_name}%",)
        ).fetchone()

        if not row:
            return json.dumps({
                "success": False,
                "message": f"CRM中未找到'{company_name}'的记录，无法更新。请先确认企业名称。"
            }, ensure_ascii=False)

        old_record = dict(row)
        actual_name = old_record["company_name"]
        changes = []

        # 更新阶段
        if new_stage and new_stage != old_record.get("stage"):
            old_stage = old_record.get("stage", "N/A")
            conn.execute(
                "UPDATE crm_records SET stage = ? WHERE company_name = ?",
                (new_stage, actual_name)
            )
            changes.append(f"阶段: {old_stage} → {new_stage}")

        # 追加跟进备注
        if follow_up_note:
            timestamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            new_note = f"[{timestamp}] {follow_up_note}"
            old_notes = old_record.get("notes", "") or ""
            updated_notes = f"{old_notes}\n{new_note}".strip()
            conn.execute(
                "UPDATE crm_records SET notes = ? WHERE company_name = ?",
                (updated_notes, actual_name)
            )
            changes.append(f"新增备注: {follow_up_note}")

        # 更新下次跟进日期
        if next_follow_up_date:
            conn.execute(
                "UPDATE crm_records SET next_follow_up = ? WHERE company_name = ?",
                (next_follow_up_date, actual_name)
            )
            changes.append(f"下次跟进: {next_follow_up_date}")

        if not changes:
            return json.dumps({
                "success": False,
                "message": "未指定任何更新内容。请提供 new_stage、follow_up_note 或 next_follow_up_date 中的至少一项。"
            }, ensure_ascii=False)

        conn.commit()

        # 查询更新后的记录
        updated_row = conn.execute(
            "SELECT * FROM crm_records WHERE company_name = ? LIMIT 1",
            (actual_name,)
        ).fetchone()

        return json.dumps({
            "success": True,
            "company_name": actual_name,
            "changes": changes,
            "updated_record": dict(updated_row) if updated_row else {},
            "updated_at": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False)
    finally:
        conn.close()


# ── 工具注册表 ────────────────────────────────────
TOOL_REGISTRY = {
    "search_enterprises": search_enterprises,
    "get_company_risk": get_company_risk,
    "get_industry_chain": get_industry_chain,
    "search_park_resources": search_park_resources,
    "query_crm_status": query_crm_status,
    "search_knowledge_base": search_knowledge_base,
    "get_external_intelligence": get_external_intelligence,
    "get_current_time": get_current_time,
    "update_crm_record": update_crm_record,
}


def execute_tool(name: str, arguments: dict) -> str:
    """统一工具执行入口"""
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
    try:
        return fn(**arguments)
    except Exception as e:
        return json.dumps({"error": f"工具执行出错: {str(e)}"}, ensure_ascii=False)
