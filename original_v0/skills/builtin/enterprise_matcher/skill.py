# -*- coding: utf-8 -*-
"""企业匹配分析器 Skill — 数据采集型（交给 LLM 做综合分析）"""
import os
import sys
import re
import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from skills.base_skill import BaseSkill

DB_PATH = os.path.join(PROJECT_ROOT, "db", "park_data.db")
GRAPH_JSON = os.path.join(PROJECT_ROOT, "db", "industry_graph.json")
logger = logging.getLogger(__name__)


class EnterpriseMatcherSkill(BaseSkill):
    PRIORITY = 80

    """企业匹配分析器

    采集企业信息、风险评估、CRM 记录、产业链关系、园区资源/政策、
    相似案例等多源数据，构建数据包交给 LLM 做综合匹配分析。
    不再使用硬编码规则打分。
    """

    def can_handle(self, context: Dict[str, Any]) -> bool:
        user_input = context.get("user_input", "").lower()

        keywords = self.triggers.get("keywords", [])
        if self._match_keywords(user_input, keywords):
            return True

        if ("分析" in user_input or "评估" in user_input or "匹配" in user_input) and \
           ("企业" in user_input or "公司" in user_input or "入驻" in user_input):
            return True

        return False

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """采集多源数据，构建 context 数据包，交给 LLM"""
        user_input = context.get("user_input", "")

        try:
            company_name = self._extract_company_name(user_input)

            if not company_name:
                return {
                    "handled": True,
                    "response": "请指定要分析的企业名称，例如：'分析芯启源半导体是否适合入驻'"
                }

            # ----- 多源数据采集 -----
            collected = {}

            # 1) 企业基本信息
            company_info = self._query_company(company_name)
            if not company_info:
                return {
                    "handled": True,
                    "response": f"未找到企业「{company_name}」的信息。请确认企业名称或先用 search_enterprises 搜索。"
                }
            collected["company_info"] = company_info

            # 2) 风险评估
            risk = self._get_risk_assessment(company_name)
            if risk:
                collected["risk_assessment"] = risk

            # 3) CRM 跟进记录
            crm = self._query_crm(company_name)
            if crm:
                collected["crm_record"] = crm

            # 4) 产业链关系
            industry = company_info.get("industry", "")
            if industry:
                chain = self._query_industry_chain(industry)
                if chain:
                    collected["industry_chain"] = chain

            # 5) 园区概况（给 LLM 对比用）
            park_stats = self._query_park_stats()
            if park_stats:
                collected["park_stats"] = park_stats

            # 6) 适用政策
            policies = self._query_matching_policies(company_info)
            if policies:
                collected["matching_policies"] = policies

            # 7) 匹配的园区资源
            resources = self._query_matching_resources(company_info)
            if resources:
                collected["matching_resources"] = resources

            # 8) 相似入驻案例
            similar = self._query_similar_cases(company_info)
            if similar:
                collected["similar_cases"] = similar

            # ----- 构建 LLM 指令 -----
            instruction = (
                f"请基于以下多源数据，综合分析「{company_name}」与光谷智创园的匹配度。\n"
                f"要求输出：\n"
                f"1. 匹配度评分（0-100）及评级（高度匹配/匹配良好/匹配一般/不匹配）\n"
                f"2. 从以下维度分析：行业契合度、产业链互补性、企业成长潜力、规模适配、风险评估\n"
                f"3. 引用真实的数据做分析（如：该企业融资到X轮，员工X人，涉及X产业链环节）\n"
                f"4. 列出匹配优势和潜在风险\n"
                f"5. 如有CRM记录，基于跟进历史给出针对性建议\n"
                f"6. 如有适用政策和匹配资源，具体推荐\n"
                f"7. 给出具体的下一步行动建议"
            )

            return {
                "handled": False,
                "context_data": collected,
                "instruction": instruction,
                "data": {
                    "company_name": company_name,
                    "skill_name": "企业匹配分析器",
                }
            }

        except Exception as e:
            logger.exception("EnterpriseMatcherSkill execute failed")
            return {"handled": False, "error": f"匹配数据采集失败: {str(e)}"}

    # ── 文本提取 ──

    def _extract_company_name(self, text: str) -> Optional[str]:
        matches = re.findall(r'["""](.*?)["""]', text)
        if matches:
            return matches[0]

        patterns = [
            r'分析(?:一下)?(?:看看)?([^\s，。、是否适合]{2,15})(?:是否|适合|匹配|的)',
            r'评估(?:一下)?(?:看看)?([^\s，。、是否适合]{2,15})(?:是否|适合|匹配|的)',
            r'([^\s，。、]{2,15})(?:是否适合|适合入驻|能否入驻)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                if name not in ['企业', '公司', '我们', '园区', '入驻', '一下', '看看', '这个', '那个']:
                    return name
        return None

    # ── 数据库查询 ──

    def _get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _query_company(self, name: str) -> Optional[Dict]:
        try:
            conn = self._get_db()
            try:
                row = conn.execute(
                    "SELECT * FROM enterprises WHERE name LIKE ? LIMIT 1",
                    (f"%{name}%",)
                ).fetchone()
            finally:
                conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.debug("EnterpriseMatcherSkill _query_company failed: %s", e)
            return None

    def _get_risk_assessment(self, company_name: str) -> Optional[Dict]:
        """调用风险评估工具"""
        try:
            from tools.implementations import get_company_risk
            result_json = get_company_risk(company_name)
            result = json.loads(result_json)
            if result.get("found"):
                return result
        except Exception as e:
            logger.debug("EnterpriseMatcherSkill _get_risk_assessment failed: %s", e)
        return None

    def _query_crm(self, name: str) -> Optional[Dict]:
        try:
            conn = self._get_db()
            try:
                row = conn.execute(
                    "SELECT * FROM crm_records WHERE company_name LIKE ? LIMIT 1",
                    (f"%{name}%",)
                ).fetchone()
            finally:
                conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.debug("EnterpriseMatcherSkill _query_crm failed: %s", e)
            return None

    def _query_industry_chain(self, industry: str) -> Optional[Dict]:
        """查询产业链关系"""
        try:
            import networkx as nx
            with open(GRAPH_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "edges" in data and "links" not in data:
                data["links"] = data["edges"]
            elif "links" in data and "edges" not in data:
                data["edges"] = data["links"]

            G = nx.node_link_graph(data, directed=True, edges="links")

            # 找匹配节点
            target = None
            for n in G.nodes():
                if industry in n or n in industry:
                    target = n
                    break
            if not target:
                return None

            upstream = [{"name": p, "relation": G.edges[p, target].get("relation", "")}
                        for p in G.predecessors(target)]
            downstream = [{"name": s, "relation": G.edges[target, s].get("relation", "")}
                          for s in G.successors(target)]

            return {
                "industry": target,
                "upstream": upstream[:5],
                "downstream": downstream[:5],
                "node_info": dict(G.nodes[target]),
            }
        except Exception as e:
            logger.debug("EnterpriseMatcherSkill _query_industry_chain failed: %s", e)
            return None

    def _query_park_stats(self) -> Optional[Dict]:
        try:
            conn = self._get_db()
            try:
                stats = {}
                stats["signed_count"] = conn.execute(
                    "SELECT COUNT(*) FROM crm_records WHERE stage='已签约'"
                ).fetchone()[0]
                stats["in_progress"] = conn.execute(
                    "SELECT COUNT(*) FROM crm_records WHERE stage IN ('初步接触','洽谈中','意向明确')"
                ).fetchone()[0]
                stats["total_resources"] = conn.execute("SELECT COUNT(*) FROM park_resources").fetchone()[0]
                stats["vacant_resources"] = conn.execute(
                    "SELECT COUNT(*) FROM park_resources WHERE status='空置'"
                ).fetchone()[0]
                stats["target_industries"] = ["半导体与集成电路", "人工智能与大数据", "生物医药与大健康"]

                # 查已入驻企业的行业分布
                rows = conn.execute(
                    "SELECT c.company_name, e.industry FROM crm_records c "
                    "LEFT JOIN enterprises e ON c.company_name = e.name "
                    "WHERE c.stage = '已签约' LIMIT 10"
                ).fetchall()
                stats["sample_tenants"] = [{"name": r[0], "industry": r[1] or "未知"} for r in rows]
            finally:
                conn.close()
            return stats
        except Exception as e:
            logger.debug("EnterpriseMatcherSkill _query_park_stats failed: %s", e)
            return None

    def _query_matching_policies(self, company_info: Dict) -> List[Dict]:
        try:
            conn = self._get_db()
            try:
                rows = conn.execute("SELECT * FROM park_policies").fetchall()
            finally:
                conn.close()

            policies = [dict(r) for r in rows]
            tags = company_info.get("tags", "")
            industry = company_info.get("industry", "")

            # 标注哪些政策可能适用
            for p in policies:
                p_name = p.get("name", "") + p.get("description", "")
                applicable = False
                if "专精特新" in tags and "专精特新" in p_name:
                    applicable = True
                elif "高新" in tags and "高新" in p_name:
                    applicable = True
                elif industry and industry in p_name:
                    applicable = True
                p["potentially_applicable"] = applicable

            return policies
        except Exception as e:
            logger.debug("EnterpriseMatcherSkill _query_matching_policies failed: %s", e)
            return []

    def _query_matching_resources(self, company_info: Dict) -> List[Dict]:
        try:
            conn = self._get_db()
            try:
                rows = conn.execute(
                    "SELECT * FROM park_resources WHERE status = '空置' LIMIT 5"
                ).fetchall()
            finally:
                conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug("EnterpriseMatcherSkill _query_matching_resources failed: %s", e)
            return []

    def _query_similar_cases(self, company_info: Dict) -> List[Dict]:
        try:
            from data.init_chromadb import get_vector_store
            store = get_vector_store()
            industry = company_info.get("industry", "企业")
            results = store.query(query=f"{industry}企业入驻匹配分析", collection="all", top_k=2)
            return [{
                "id": r.get("id", ""),
                "collection": r.get("collection", ""),
                "content": r["content"],
                "title": (r.get("metadata") or {}).get("title", ""),
                "similarity": r.get("similarity"),
            }
                    for r in results]
        except Exception as e:
            logger.debug("EnterpriseMatcherSkill _query_similar_cases failed: %s", e)
            return []
