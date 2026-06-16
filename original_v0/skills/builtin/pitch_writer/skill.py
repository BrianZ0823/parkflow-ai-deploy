# -*- coding: utf-8 -*-
"""招商话术生成器 Skill — 数据采集型（交给 LLM 完成最终写作）"""
import os
import sys
import json
import re
import sqlite3
import logging
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from skills.base_skill import BaseSkill

DB_PATH = os.path.join(PROJECT_ROOT, "db", "park_data.db")
NEWS_JSON = os.path.join(PROJECT_ROOT, "external_api", "enterprise_news.json")
logger = logging.getLogger(__name__)


class PitchWriterSkill(BaseSkill):
    PRIORITY = 80

    """招商话术生成器

    采集企业信息、园区政策、资源、CRM记录、相似案例等多源数据，
    构建结构化 context 数据包交给 LLM 完成个性化话术写作。
    不再输出硬编码模板。
    """

    def can_handle(self, context: Dict[str, Any]) -> bool:
        user_input = context.get("user_input", "").lower()

        keywords = self.triggers.get("keywords", [])
        if self._match_keywords(user_input, keywords):
            return True

        if ("写" in user_input or "生成" in user_input or "起草" in user_input) and \
           ("邮件" in user_input or "话术" in user_input or "方案" in user_input or
            "演讲" in user_input or "推介" in user_input):
            return True

        return False

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """采集数据，构建 context 数据包，交给 LLM 生成"""
        user_input = context.get("user_input", "")

        try:
            target_company = self._extract_company_name(user_input)
            pitch_type = self._extract_pitch_type(user_input)
            highlights = self._extract_highlights(user_input)

            # ----- 多源数据采集 -----
            collected = {}

            # 1) 企业基本信息
            company_info = None
            if target_company:
                company_info = self._query_company(target_company)
                if company_info:
                    collected["company_info"] = company_info

            # 2) CRM 跟进历史
            if target_company:
                crm = self._query_crm(target_company)
                if crm:
                    collected["crm_history"] = crm

            # 3) 园区真实政策
            policies = self._query_policies()
            if policies:
                collected["park_policies"] = policies

            # 4) 匹配的园区资源
            resources = self._query_matching_resources(company_info)
            if resources:
                collected["matching_resources"] = resources

            # 5) 企业新闻动态
            if target_company:
                news = self._query_news(target_company)
                if news:
                    collected["recent_news"] = news

            # 6) 相似招商案例（从向量库）
            similar = self._query_similar_cases(company_info)
            if similar:
                collected["similar_cases"] = similar

            # ----- 构建 LLM 指令 -----
            type_names = {
                "email": "招商邮件",
                "speech": "招商推介演讲稿",
                "proposal": "企业入驻定制方案",
            }
            type_label = type_names.get(pitch_type, "招商邮件")

            highlight_text = ""
            if highlights:
                highlight_text = f"\n用户特别要求重点介绍：{', '.join(highlights)}"

            company_label = f"针对「{target_company}」的" if target_company else ""

            instruction = (
                f"请基于以下真实数据，生成一份{company_label}{type_label}。\n"
                f"要求：\n"
                f"1. 引用真实的园区政策数据（如有），不要编造政策内容\n"
                f"2. 如果有企业信息，要体现对该企业行业和需求的了解\n"
                f"3. 如果有CRM跟进记录，语气要体现之前的沟通基础\n"
                f"4. 推荐的园区资源要与企业规模和行业匹配\n"
                f"5. 如有相似成功案例，可适当引用增强说服力\n"
                f"6. 语气专业热情，体现招商经理的专业素养"
                f"{highlight_text}"
            )

            return {
                "handled": False,          # 不拦截，交给 LLM
                "context_data": collected,  # 结构化数据包
                "instruction": instruction,
                "data": {
                    "pitch_type": pitch_type,
                    "target_company": target_company,
                    "skill_name": "招商话术生成器",
                }
            }

        except Exception as e:
            logger.exception("PitchWriterSkill execute failed")
            return {"handled": False, "error": f"话术数据采集失败: {str(e)}"}

    # ── 数据提取工具 ──

    def _extract_company_name(self, text: str) -> Optional[str]:
        matches = re.findall(r'["""](.*?)[""\"]', text)
        if matches:
            return matches[0]

        patterns = [
            r'给\s*([^\s，。、]{2,15})\s*[写发生]',
            r'对\s*([^\s，。、]{2,15})\s*[的]',
            r'向\s*([^\s，。、]{2,15})\s*[发写]',
            r'针对\s*([^\s，。、]{2,15})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                if name not in ['企业', '公司', '我们', '园区', '一下', '看看', '一份']:
                    return name
        return None

    def _extract_pitch_type(self, text: str) -> str:
        if "邮件" in text:
            return "email"
        elif "演讲" in text or "讲稿" in text or "推介" in text:
            return "speech"
        elif "方案" in text or "计划" in text:
            return "proposal"
        return "email"

    def _extract_highlights(self, text: str) -> List[str]:
        highlights = []
        patterns = [
            r'重点[介绍说明]*([^，。、]+)',
            r'强调([^，。、]+)',
            r'突出([^，。、]+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            highlights.extend(matches)
        return highlights

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
            logger.debug("PitchWriterSkill _query_company failed: %s", e)
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
            logger.debug("PitchWriterSkill _query_crm failed: %s", e)
            return None

    def _query_policies(self) -> List[Dict]:
        try:
            conn = self._get_db()
            try:
                rows = conn.execute("SELECT * FROM park_policies").fetchall()
            finally:
                conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug("PitchWriterSkill _query_policies failed: %s", e)
            return []

    def _query_matching_resources(self, company_info: Optional[Dict]) -> List[Dict]:
        try:
            conn = self._get_db()
            try:
                sql = "SELECT * FROM park_resources WHERE status = '空置'"
                if company_info:
                    employees = company_info.get("employees", 0)
                    if employees and employees > 200:
                        sql += " AND type IN ('office', 'factory')"
                    elif employees and employees < 30:
                        sql += " AND type = 'office'"
                sql += " LIMIT 5"
                rows = conn.execute(sql).fetchall()
            finally:
                conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug("PitchWriterSkill _query_matching_resources failed: %s", e)
            return []

    def _query_news(self, company_name: str) -> List[Dict]:
        try:
            if not os.path.exists(NEWS_JSON):
                return []
            with open(NEWS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            news = data.get("news", [])
            return [n for n in news
                    if company_name in n.get("company", "")
                    or n.get("company", "") in company_name][:3]
        except Exception as e:
            logger.debug("PitchWriterSkill _query_news failed: %s", e)
            return []

    def _query_similar_cases(self, company_info: Optional[Dict]) -> List[Dict]:
        """从向量知识库查找相似案例"""
        try:
            from data.init_chromadb import get_vector_store
            store = get_vector_store()
            query = "成功入驻案例"
            if company_info:
                industry = company_info.get("industry", "")
                if industry:
                    query = f"{industry}企业入驻案例"
            results = store.query(query=query, collection="all", top_k=2)
            return [{
                "id": r.get("id", ""),
                "collection": r.get("collection", ""),
                "content": r["content"],
                "title": (r.get("metadata") or {}).get("title", ""),
                "similarity": r.get("similarity"),
            }
                    for r in results]
        except Exception as e:
            logger.debug("PitchWriterSkill _query_similar_cases failed: %s", e)
            return []
