# -*- coding: utf-8 -*-
"""招商报告生成器 Skill — 支持日报/周报/月报差异化报告"""
import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 将项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from skills.base_skill import BaseSkill

DB_PATH = os.path.join(PROJECT_ROOT, "db", "park_data.db")
logger = logging.getLogger(__name__)


class ReportGeneratorSkill(BaseSkill):
    PRIORITY = 90

    """招商报告生成器

    根据报告类型（日报/周报/月报）生成差异化的招商报告：
    - 日报：聚焦当日跟进动态、待办事项
    - 周报：7天内的跟进汇总、阶段转化分析、本周重点
    - 月报：30天全景分析、趋势对比、战略建议
    """

    # 报告类型配置
    REPORT_CONFIG = {
        "daily": {
            "name": "日报",
            "days_range": 1,
            "emoji": "📋",
        },
        "weekly": {
            "name": "周报",
            "days_range": 7,
            "emoji": "📊",
        },
        "monthly": {
            "name": "月报",
            "days_range": 30,
            "emoji": "📈",
        },
    }

    def can_handle(self, context: Dict[str, Any]) -> bool:
        """判断是否能处理当前请求"""
        user_input = context.get("user_input", "").lower()

        # 关键词匹配
        keywords = self.triggers.get("keywords", [])
        if self._match_keywords(user_input, keywords):
            return True

        # 额外模式匹配
        report_patterns = [
            ("生成", "报告"), ("写", "报告"), ("出", "周报"),
            ("出", "日报"), ("出", "月报"), ("汇总", "数据"),
            ("招商", "总结"), ("工作", "汇报"),
        ]
        for kw1, kw2 in report_patterns:
            if kw1 in user_input and kw2 in user_input:
                return True

        return False

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行报告生成"""
        user_input = context.get("user_input", "")

        try:
            report_type = self._detect_report_type(user_input)
            config = self.REPORT_CONFIG[report_type]
            now = datetime.now()

            # 计算时间窗口
            cutoff_date = (now - timedelta(days=config["days_range"])).strftime("%Y-%m-%d")

            # 采集数据
            data = self._collect_data(report_type, cutoff_date, now)

            # 生成对应类型报告
            if report_type == "daily":
                report = self._generate_daily(data, now)
            elif report_type == "weekly":
                report = self._generate_weekly(data, now)
            else:
                report = self._generate_monthly(data, now)

            return {
                "handled": True,
                "response": report,
                "data": {
                    "report_type": report_type,
                    "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                }
            }
        except Exception as e:
            logger.exception("ReportGeneratorSkill execute failed")
            return {
                "handled": False,
                "error": f"报告生成失败: {str(e)}"
            }

    def _detect_report_type(self, text: str) -> str:
        """检测报告类型"""
        if "日报" in text or "今日" in text or "今天" in text:
            return "daily"
        elif "月报" in text or "本月" in text or "月度" in text:
            return "monthly"
        else:
            return "weekly"

    def _get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _collect_data(self, report_type: str, cutoff_date: str, now: datetime) -> Dict[str, Any]:
        """采集数据，根据报告类型做时间过滤"""
        conn = self._get_db()
        try:
            c = conn.cursor()
            data = {}

            # ── 通用指标（快照，不分时间） ──
            # CRM 各阶段
            stage_stats = {}
            for row in c.execute(
                "SELECT stage, COUNT(*) as cnt FROM crm_records GROUP BY stage"
            ).fetchall():
                stage_stats[row["stage"]] = row["cnt"]
            data["stage_stats"] = stage_stats
            data["total_crm"] = sum(stage_stats.values())
            data["signed_count"] = stage_stats.get("已签约", 0)
            data["in_progress"] = sum(stage_stats.get(s, 0) for s in ["初步接触", "洽谈中", "意向明确"])
            data["lost_count"] = stage_stats.get("已流失", 0)

            # OPC企业池
            data["pool_count"] = c.execute("SELECT COUNT(*) FROM enterprises").fetchone()[0]

            # 园区资源
            total_res = c.execute("SELECT COUNT(*) FROM park_resources").fetchone()[0]
            vacant_res = c.execute("SELECT COUNT(*) FROM park_resources WHERE status='空置'").fetchone()[0]
            data["total_resources"] = total_res
            data["vacant_resources"] = vacant_res
            data["occupied_resources"] = total_res - vacant_res
            data["occupancy_rate"] = round((total_res - vacant_res) / max(total_res, 1) * 100, 1)

            # 资源类型明细
            data["resource_types"] = [
                dict(row) for row in c.execute(
                    "SELECT type, COUNT(*) as total, "
                    "SUM(CASE WHEN status='空置' THEN 1 ELSE 0 END) as vacant "
                    "FROM park_resources GROUP BY type"
                ).fetchall()
            ]

            # ── 时间窗口内的跟进动态 ──
            recent_contacts = c.execute(
                "SELECT company_name, stage, last_contact, interest_level, notes "
                "FROM crm_records "
                "WHERE last_contact >= ? AND stage NOT IN ('已签约', '已流失') "
                "ORDER BY last_contact DESC",
                (cutoff_date,)
            ).fetchall()
            data["recent_contacts"] = [dict(row) for row in recent_contacts]
            data["period_contact_count"] = len(recent_contacts)

            # 期间内新签约（last_contact 在窗口内且阶段为已签约）
            new_signed = c.execute(
                "SELECT company_name, last_contact FROM crm_records "
                "WHERE last_contact >= ? AND stage = '已签约' "
                "ORDER BY last_contact DESC",
                (cutoff_date,)
            ).fetchall()
            data["new_signed"] = [dict(row) for row in new_signed]

            # 期间内新流失
            new_lost = c.execute(
                "SELECT company_name, last_contact FROM crm_records "
                "WHERE last_contact >= ? AND stage = '已流失' "
                "ORDER BY last_contact DESC",
                (cutoff_date,)
            ).fetchall()
            data["new_lost"] = [dict(row) for row in new_lost]

            # 高意向在谈企业
            high_interest = c.execute(
                "SELECT company_name, stage, interest_level, last_contact "
                "FROM crm_records "
                "WHERE interest_level = '高' AND stage NOT IN ('已签约', '已流失') "
                "ORDER BY last_contact DESC"
            ).fetchall()
            data["high_interest"] = [dict(row) for row in high_interest]

            # 待跟进（有 next_follow_up 的）
            pending_followups = c.execute(
                "SELECT company_name, stage, next_follow_up "
                "FROM crm_records "
                "WHERE next_follow_up IS NOT NULL AND next_follow_up != '' "
                "AND stage NOT IN ('已签约', '已流失') "
                "ORDER BY next_follow_up ASC"
            ).fetchall()
            data["pending_followups"] = [dict(row) for row in pending_followups]

            # ── 月报专用：行业分布 ──
            if report_type == "monthly":
                data["top_industries"] = [
                    (row["industry"], row["cnt"]) for row in c.execute(
                        "SELECT industry, COUNT(*) as cnt FROM enterprises "
                        "GROUP BY industry ORDER BY cnt DESC LIMIT 8"
                    ).fetchall()
                ]
                # 各阶段意向分布
                data["interest_distribution"] = [
                    dict(row) for row in c.execute(
                        "SELECT stage, interest_level, COUNT(*) as cnt FROM crm_records "
                        "WHERE stage NOT IN ('已签约', '已流失') "
                        "GROUP BY stage, interest_level "
                        "ORDER BY stage, interest_level"
                    ).fetchall()
                ]

            return data
        finally:
            conn.close()

    # ════════════════════════════════════════════
    #  日报：聚焦当日动态 + 待办
    # ════════════════════════════════════════════
    def _generate_daily(self, data: Dict, now: datetime) -> str:
        weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        parts = []

        parts.append(f"# 📋 光谷智创园 · 招商日报\n")
        parts.append(f"**日期**: {now.strftime('%Y年%m月%d日')}（{weekday}）\n")
        parts.append("---\n")

        # 一、今日核心数据
        parts.append("## 一、今日核心数据\n")
        parts.append(f"- 📞 今日跟进企业：**{data['period_contact_count']}** 家")
        parts.append(f"- 🏢 园区当前入驻：{data['signed_count']} 家")
        parts.append(f"- 🔄 在谈总数：{data['in_progress']} 家\n")

        # 二、今日跟进记录
        parts.append("## 二、今日跟进记录\n")
        if data["recent_contacts"]:
            parts.append("| 企业 | 阶段 | 意向 |")
            parts.append("|------|------|------|")
            for ent in data["recent_contacts"]:
                parts.append(f"| {ent['company_name']} | {ent['stage']} | {ent['interest_level']} |")
        else:
            parts.append("*今日暂无新的跟进记录。*")
        parts.append("")

        # 三、明日待办
        parts.append("## 三、近期待跟进\n")
        if data["pending_followups"]:
            parts.append("| 企业 | 阶段 | 计划跟进日期 |")
            parts.append("|------|------|------------|")
            for ent in data["pending_followups"][:5]:
                parts.append(f"| {ent['company_name']} | {ent['stage']} | {ent['next_follow_up']} |")
        else:
            parts.append("*暂无设定跟进日期的企业。建议为高意向企业设置跟进提醒。*")
        parts.append("")

        # 四、高意向关注
        if data["high_interest"]:
            parts.append("## 四、🔥 高意向企业提醒\n")
            hi_names = [e["company_name"] for e in data["high_interest"][:5]]
            parts.append(f"共 **{len(data['high_interest'])}** 家高意向企业在谈，重点关注：{', '.join(hi_names)}\n")

        parts.append("---")
        parts.append(f"*招商日报 · 自动生成 | {now.strftime('%H:%M:%S')}*")
        return "\n".join(parts)

    # ════════════════════════════════════════════
    #  周报：7天汇总 + 阶段分析 + 资源利用
    # ════════════════════════════════════════════
    def _generate_weekly(self, data: Dict, now: datetime) -> str:
        weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        week_start = (now - timedelta(days=6)).strftime("%m月%d日")
        week_end = now.strftime("%m月%d日")
        parts = []

        parts.append(f"# 📊 光谷智创园 · 招商周报\n")
        parts.append(f"**报告周期**: {week_start} — {week_end}（{weekday}生成）\n")
        parts.append("---\n")

        # 一、本周关键指标
        parts.append("## 一、本周关键指标\n")
        parts.append("| 指标 | 数值 |")
        parts.append("|------|------|")
        parts.append(f"| 📞 本周跟进企业 | **{data['period_contact_count']}** 家 |")
        parts.append(f"| ✅ 本周新签约 | **{len(data['new_signed'])}** 家 |")
        parts.append(f"| ❌ 本周新流失 | {len(data['new_lost'])} 家 |")
        parts.append(f"| 🏢 累计入驻 | {data['signed_count']} 家 |")
        parts.append(f"| 🔄 在谈总数 | {data['in_progress']} 家 |")
        parts.append(f"| 🏗️ 园区使用率 | {data['occupancy_rate']}% |")
        parts.append("")

        # 二、CRM 阶段分布
        parts.append("## 二、CRM 客户阶段分布\n")
        stage_order = ["初步接触", "洽谈中", "意向明确", "已签约", "已流失"]
        stage_emojis = {"初步接触": "🟡", "洽谈中": "🔵", "意向明确": "🟢", "已签约": "✅", "已流失": "⛔"}
        for stage in stage_order:
            count = data["stage_stats"].get(stage, 0)
            bar = "█" * min(count, 30)
            parts.append(f"- {stage_emojis.get(stage, '•')} **{stage}**: {count} 家 {bar}")
        parts.append("")

        # 三、本周跟进动态
        parts.append("## 三、本周跟进动态\n")
        if data["recent_contacts"]:
            parts.append("| 企业 | 阶段 | 最近联系 | 意向 |")
            parts.append("|------|------|----------|------|")
            for ent in data["recent_contacts"][:10]:
                parts.append(f"| {ent['company_name']} | {ent['stage']} | {ent['last_contact']} | {ent['interest_level']} |")
        else:
            parts.append("*本周暂无跟进记录。*")
        parts.append("")

        # 四、园区资源利用
        parts.append("## 四、园区资源利用率\n")
        parts.append("| 类型 | 总计 | 空置 | 利用率 |")
        parts.append("|------|------|------|--------|")
        for rt in data["resource_types"]:
            used = rt["total"] - rt["vacant"]
            rate = round(used / max(rt["total"], 1) * 100, 1)
            parts.append(f"| {rt['type']} | {rt['total']} | {rt['vacant']} | {rate}% |")
        parts.append("")

        # 五、重点跟进
        if data["high_interest"]:
            parts.append("## 五、🔥 高意向重点企业\n")
            parts.append("| 企业 | 阶段 | 最近联系 |")
            parts.append("|------|------|----------|")
            for ent in data["high_interest"][:8]:
                parts.append(f"| {ent['company_name']} | {ent['stage']} | {ent.get('last_contact', '-')} |")
        parts.append("")

        # 六、下周工作建议
        parts.append("## 六、下周工作建议\n")
        self._append_suggestions(parts, data)

        parts.append("---")
        parts.append(f"*招商周报 · 自动生成 | {now.strftime('%Y-%m-%d %H:%M:%S')}*")
        return "\n".join(parts)

    # ════════════════════════════════════════════
    #  月报：30天全景 + 趋势 + 战略
    # ════════════════════════════════════════════
    def _generate_monthly(self, data: Dict, now: datetime) -> str:
        month_label = now.strftime("%Y年%m月")
        parts = []

        parts.append(f"# 📈 光谷智创园 · 招商月报\n")
        parts.append(f"**报告月份**: {month_label}\n")
        parts.append("---\n")

        # 一、月度总览
        parts.append("## 一、月度总览\n")
        parts.append("| 指标 | 数值 | 说明 |")
        parts.append("|------|------|------|")
        parts.append(f"| 📞 本月跟进企业 | **{data['period_contact_count']}** | 过去30天内有联系记录 |")
        parts.append(f"| ✅ 本月新签约 | **{len(data['new_signed'])}** | 本月完成签约入驻 |")
        parts.append(f"| ❌ 本月新流失 | {len(data['new_lost'])} | 本月标记为流失 |")
        net = len(data['new_signed']) - len(data['new_lost'])
        net_str = f"+{net}" if net >= 0 else str(net)
        parts.append(f"| 📊 净增长 | **{net_str}** | 签约 - 流失 |")
        parts.append(f"| 🏢 累计入驻 | {data['signed_count']} | |")
        parts.append(f"| 🔄 在谈总数 | {data['in_progress']} | 初步接触+洽谈中+意向明确 |")
        parts.append(f"| 🎯 OPC企业池 | {data['pool_count']} | 候选目标企业库 |")
        parts.append(f"| 🏗️ 园区使用率 | {data['occupancy_rate']}% | ({data['occupied_resources']}/{data['total_resources']}) |")
        parts.append("")

        # 二、CRM 转化漏斗
        parts.append("## 二、CRM 客户阶段分布（转化漏斗）\n")
        stage_order = ["初步接触", "洽谈中", "意向明确", "已签约", "已流失"]
        stage_emojis = {"初步接触": "🟡", "洽谈中": "🔵", "意向明确": "🟢", "已签约": "✅", "已流失": "⛔"}
        total_crm = data["total_crm"]
        for stage in stage_order:
            count = data["stage_stats"].get(stage, 0)
            pct = round(count / max(total_crm, 1) * 100, 1)
            bar = "█" * min(count, 30)
            parts.append(f"- {stage_emojis.get(stage, '•')} **{stage}**: {count} 家 ({pct}%) {bar}")
        parts.append("")

        # 三、本月新签约/流失明细
        if data["new_signed"]:
            parts.append("## 三、本月新签约企业\n")
            parts.append("| 企业 | 签约日期 |")
            parts.append("|------|----------|")
            for ent in data["new_signed"][:10]:
                parts.append(f"| {ent['company_name']} | {ent['last_contact']} |")
            parts.append("")

        if data["new_lost"]:
            parts.append("## 本月流失企业\n")
            parts.append("| 企业 | 流失日期 |")
            parts.append("|------|----------|")
            for ent in data["new_lost"]:
                parts.append(f"| {ent['company_name']} | {ent['last_contact']} |")
            parts.append("")

        # 四、园区资源利用率
        parts.append("## 四、园区资源利用率\n")
        parts.append("| 类型 | 总计 | 空置 | 利用率 |")
        parts.append("|------|------|------|--------|")
        for rt in data["resource_types"]:
            used = rt["total"] - rt["vacant"]
            rate = round(used / max(rt["total"], 1) * 100, 1)
            parts.append(f"| {rt['type']} | {rt['total']} | {rt['vacant']} | {rate}% |")
        parts.append("")

        # 五、OPC企业池行业分布
        if data.get("top_industries"):
            parts.append("## 五、OPC企业池行业分布（Top 8）\n")
            for industry, cnt in data["top_industries"]:
                bar = "▓" * min(cnt // 2, 20)
                parts.append(f"- **{industry}**: {cnt} 家 {bar}")
            parts.append("")

        # 六、高意向在谈企业
        if data["high_interest"]:
            parts.append("## 六、🔥 高意向重点企业\n")
            parts.append("| 企业 | 阶段 | 最近联系 |")
            parts.append("|------|------|----------|")
            for ent in data["high_interest"][:10]:
                parts.append(f"| {ent['company_name']} | {ent['stage']} | {ent.get('last_contact', '-')} |")
            parts.append("")

        # 七、下月工作建议
        parts.append("## 七、下月战略建议\n")
        self._append_monthly_strategy(parts, data)

        parts.append("---")
        parts.append(f"*招商月报 · 自动生成 | {now.strftime('%Y-%m-%d %H:%M:%S')}*")
        return "\n".join(parts)

    # ── 通用建议生成 ──
    def _append_suggestions(self, parts: List[str], data: Dict):
        intent_clear = data["stage_stats"].get("意向明确", 0)
        if intent_clear > 0:
            parts.append(f"📌 有 **{intent_clear}** 家意向明确企业待推进签约，建议优先跟进")
        negotiating = data["stage_stats"].get("洽谈中", 0)
        if negotiating > 0:
            parts.append(f"📌 **{negotiating}** 家洽谈中企业需持续跟进")
        if data["vacant_resources"] > 0:
            parts.append(f"🏗️ 仍有 {data['vacant_resources']} 处资源空置，建议加大推广力度")
        if data["high_interest"]:
            top = [e["company_name"] for e in data["high_interest"][:3]]
            parts.append(f"🔥 重点关注: {', '.join(top)}")
        parts.append("")

    def _append_monthly_strategy(self, parts: List[str], data: Dict):
        # 转化率分析
        intent_clear = data["stage_stats"].get("意向明确", 0)
        negotiating = data["stage_stats"].get("洽谈中", 0)
        initial = data["stage_stats"].get("初步接触", 0)

        if intent_clear > 0:
            parts.append(f"📌 **签约攻坚**：{intent_clear} 家意向明确企业是下月签约重点，建议逐一制定签约推进方案")
        if negotiating > 0:
            parts.append(f"📌 **转化提升**：推动 {negotiating} 家洽谈中企业进入意向明确阶段，可组织园区参观或政策宣讲")
        if initial > 0:
            parts.append(f"📌 **线索培育**：{initial} 家初步接触企业需加强沟通频次，建立信任关系")

        if data["lost_count"] > 0:
            parts.append(f"⚠️ **流失分析**：累计流失 {data['lost_count']} 家企业，建议复盘流失原因并完善招商策略")

        net_signed = len(data["new_signed"])
        vacancy = data["vacant_resources"]
        if vacancy > 0 and net_signed == 0:
            parts.append(f"🏗️ **资源去化**：{vacancy} 处空置资源，本月零新签约，建议加大线上线下推广力度")
        elif vacancy > 0:
            parts.append(f"🏗️ **资源去化**：仍有 {vacancy} 处空置，建议针对性匹配在谈企业需求")

        parts.append(f"🎯 **企业池运营**：OPC企业池 {data['pool_count']} 家，建议持续补充优质候选企业")
        parts.append("")
