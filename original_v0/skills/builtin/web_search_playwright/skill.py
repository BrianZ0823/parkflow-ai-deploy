# -*- coding: utf-8 -*-
"""
Playwright Web Search Skill
使用 Playwright MCP 执行网页搜索并提取结果
修复版：改善结果提取 + 自动点击进入搜索结果抓取正文
"""
import json
import logging
import re
import urllib.parse
from typing import Dict, Any, List, Optional
from openai import OpenAI
from agent.config import LLM_CONFIG

try:
    from skills.base_skill import BaseSkill
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from skills.base_skill import BaseSkill

logger = logging.getLogger(__name__)

# 最多自动点击几个搜索结果去抓取正文
MAX_DETAIL_PAGES = 3
# 每个详情页正文截取的最大字符数
MAX_CONTENT_CHARS = 1500


class PlaywrightWebSearchSkill(BaseSkill):
    PRIORITY = 60

    """基于 Playwright MCP 的免费网页搜索技能（含自动阅读正文）"""
    DEFAULT_PARK_CONTEXT = {
        "park_name": "光谷智创园",
        "location": "武汉东湖高新区",
        "industries": ["半导体", "人工智能", "生物医药"],
    }

    def can_handle(self, context: Dict[str, Any]) -> bool:
        user_input = context.get("user_input", "")
        text = user_input.strip().lower()
        if not text:
            return False

        # 明确要求上网/网页搜索时才触发，避免拦截本地数据库问题
        explicit_web_intent = [
            "上网", "网上", "互联网", "网页", "网站", "浏览器",
            "最新", "新闻", "资讯", "舆情", "公开信息",
            "search", "look up", "google", "bing", "web",
        ]
        has_web_intent = any(k in text for k in explicit_web_intent)

        # 园区内部数据问题（企业/政策/资源/入驻/CRM）默认交给本地工具链
        local_data_terms = [
            "园区", "入驻", "企业", "公司", "crm", "客户",
            "政策", "资源", "招商", "楼宇", "厂房", "办公室",
            "匹配", "评估", "签约", "线索",
        ]
        asks_local_data = any(k in text for k in local_data_terms)

        if asks_local_data and not has_web_intent:
            return False

        # 兜底：存在典型搜索口语且未命中本地数据问法时触发
        generic_search_terms = ["搜索", "搜一下", "查一下", "帮我查"]
        return has_web_intent or self._match_keywords(text, generic_search_terms)

    def _extract_query(self, user_input: str) -> str:
        text = user_input.strip()
        patterns = [
            r"^(请)?(帮我)?(上网)?(在网上)?(搜索|搜一下|查一下|帮我查)\s*",
            r"^(please\s+)?(search|look up|google)\s+",
        ]
        for p in patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE).strip()
        # 兜底清理口语前缀
        fillers = ["帮我", "上网", "在网上", "搜一下", "查一下", "搜索", "请"]
        for token in fillers:
            if text.startswith(token):
                text = text[len(token):].strip()
        text = re.sub(r"^[，。！？、\s]+", "", text)
        return text or user_input.strip()

    def _get_tool_names(self, all_tools: List[Dict[str, Any]]) -> set:
        return {t["function"]["name"] for t in all_tools if "function" in t}

    def _extract_items_from_eval_result(self, raw: str) -> List[Dict[str, str]]:
        """从 browser_evaluate 返回文本中提取 JSON 数组结果"""
        if not raw:
            return []

        # 优先取 "### Result" 段
        result_part = raw
        marker = "### Result"
        if marker in raw:
            after = raw.split(marker, 1)[1]
            result_part = after.split("###", 1)[0].strip()

        # 先尝试双层 JSON（Playwright 常返回被 JSON 字符串包裹的 JSON）
        try:
            parsed = json.loads(result_part)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, list):
                return [x for x in parsed if isinstance(x, dict)]
        except Exception:
            pass

        # 退化为截取第一个 JSON 数组
        start = result_part.find("[")
        end = result_part.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(result_part[start:end + 1])
                if isinstance(parsed, list):
                    return [x for x in parsed if isinstance(x, dict)]
            except Exception:
                return []
        return []

    def _extract_items_from_snapshot(self, snapshot: str) -> List[Dict[str, str]]:
        """从 snapshot 文本中提取链接和标题（兼容 Bing SERP 多种格式）"""
        if not snapshot:
            return []

        lines = snapshot.splitlines()
        items = []
        seen = set()

        # ── 方式 1：查找 /url: 标记 ──
        for i, line in enumerate(lines):
            if "/url:" not in line:
                continue
            url = line.split("/url:", 1)[1].strip()
            if not url.startswith("http"):
                continue
            if self._should_skip_url(url):
                continue
            if url in seen:
                continue

            title = self._find_title_near(lines, i)
            seen.add(url)
            items.append({"title": title[:120], "url": url})
            if len(items) >= 8:
                break

        # ── 方式 2：如果方式 1 没有足够结果，尝试从 link 行提取 ──
        if len(items) < 3:
            for i, line in enumerate(lines):
                # Playwright snapshot 格式: - link "Title Text" [ref=xxx] /url:...
                m = re.search(r'- link "(.+?)".*?/url:(https?://\S+)', line)
                if m:
                    title = m.group(1).strip()
                    url = m.group(2).strip()
                    if self._should_skip_url(url) or url in seen:
                        continue
                    if len(title) < 4:
                        continue
                    seen.add(url)
                    items.append({"title": title[:120], "url": url})
                    if len(items) >= 8:
                        break

        # ── 方式 3：更宽泛地提取 http 链接 ──
        if len(items) < 3:
            for i, line in enumerate(lines):
                urls_in_line = re.findall(r'(https?://[^\s\]"<>]+)', line)
                for url in urls_in_line:
                    if self._should_skip_url(url) or url in seen:
                        continue
                    title = self._find_title_near(lines, i)
                    seen.add(url)
                    items.append({"title": title[:120], "url": url})
                    if len(items) >= 8:
                        break
                if len(items) >= 8:
                    break

        return items[:8]

    def _should_skip_url(self, url: str) -> bool:
        """判断 URL 是否应当跳过（广告、搜索引擎内部链接等）"""
        if not url:
            return True
        lowered = url.lower()
        # 跳过搜索引擎内部页面
        skip_domains = [
            "duckduckgo.com",
            "google.com/search",
            "bing.com/images",
            "bing.com/videos",
            "bing.com/maps",
            "bing.com/aclick",    # Bing 广告
            "microsoftstart.com",
            "go.microsoft.com",
            "login.microsoftonline.com",
            "javascript:",
        ]
        for domain in skip_domains:
            if domain in lowered:
                return True
        # 但不跳过 Bing 搜索结果的跳转链接和新闻链接
        # bing.com/ck/a 是 Bing 搜索结果的正常跳转链接
        if "bing.com" in lowered:
            allowed_patterns = ["/ck/a", "/news/apiclick", "url="]
            if not any(p in lowered for p in allowed_patterns):
                # 是纯 bing.com 内部页面（搜索框等），跳过
                return True
        return False

    def _find_title_near(self, lines: List[str], target_idx: int) -> str:
        """在目标行附近寻找标题文本"""
        # 先向上找 link "title" 格式
        for j in range(max(0, target_idx - 5), target_idx + 1):
            m = re.search(r'- link "([^"]+)"', lines[j])
            if m:
                return m.group(1).strip()
        # 再向上找 heading 格式
        for j in range(max(0, target_idx - 5), target_idx + 1):
            m = re.search(r'- heading "([^"]+)"', lines[j])
            if m:
                return m.group(1).strip()
        # 再向上找有文本内容的行
        for j in range(max(0, target_idx - 3), target_idx):
            text = lines[j].strip().lstrip("- ")
            if len(text) > 6 and not text.startswith("http"):
                return text[:80]
        return "未命名结果"

    def _is_bot_challenge(self, text: str) -> bool:
        if not text:
            return False
        lowered = text.lower()
        signals = [
            "confirm you're not a robot",
            "bots use duckduckgo too",
            "select all squares",
            "captcha",
            "verify you are human",
            "unusual traffic",
            "one last step",
            "solve the challenge below to continue",
            "please solve the challenge",
            "challenge below",
        ]
        return any(s in lowered for s in signals)

    def _normalize_url(self, url: str) -> str:
        """将 bing news 跳转链接还原为原始新闻链接"""
        if not url:
            return ""
        try:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            # Bing news apiclick
            if "url" in query and query["url"]:
                return query["url"][0]
            # Bing /ck/a 跳转链接中的 u 参数
            if "u" in query and query["u"]:
                u_val = query["u"][0]
                if u_val.startswith("a1") and "http" in u_val:
                    # 格式: a1aHR0cHM6... (base64)
                    pass  # 解码复杂，暂保留原URL
        except Exception:
            pass
        return url

    def _build_fallback_queries(self, query: str) -> List[str]:
        """当原始查询无结果时，生成更可检索的回退查询"""
        q = query.strip()
        candidates = []

        # 去掉时间和口语噪音词
        simplified = re.sub(r"(这周|本周|最近|近期|一下|一下子|帮我|上网|在网上|的)", " ", q)
        simplified = re.sub(r"\s+", " ", simplified).strip()
        if simplified and simplified != q:
            candidates.append(simplified)

        # 园区场景增加更高命中词
        if "园区" in q:
            if "新闻" not in simplified:
                candidates.append(f"{simplified} 新闻".strip())
            candidates.append(f"{simplified} 招商 新闻".strip())
            candidates.append("园区 招商 新闻")
            candidates.append("武汉 园区 新闻")

        # 去重并删除空项
        uniq = []
        seen = set()
        for item in candidates:
            item = item.strip()
            if item and item not in seen:
                seen.add(item)
                uniq.append(item)
        return uniq[:5]

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return {}

    def _call_json_tool(self, mcp_client: Any, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            raw = mcp_client.call_tool(tool_name, args)
            return self._extract_json_object(raw)
        except Exception as e:
            logger.warning("[PlaywrightWebSearchSkill] 预查询工具失败 %s: %s", tool_name, e)
            return {}

    def _extract_company_candidate(self, user_input: str) -> str:
        patterns = [
            r"搜一下(.{2,30}?公司)",
            r"查询(.{2,30}?公司)",
            r"查一下(.{2,30}?公司)",
            r"了解一下(.{2,30}?公司)",
            r"([A-Za-z0-9\u4e00-\u9fff]{2,40}(?:公司|集团|科技|股份|有限责任公司))",
        ]
        text = user_input.strip()
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1).strip("，。！？,. ")
        return ""

    def _collect_rewrite_context(self, user_input: str, mcp_client: Any, tool_names: set) -> Dict[str, Any]:
        context = {"park": dict(self.DEFAULT_PARK_CONTEXT)}

        if "mcp_sqlite_db_search_park_resources" in tool_names:
            park_res = self._call_json_tool(mcp_client, "mcp_sqlite_db_search_park_resources", {"resource_type": "all"})
            if park_res:
                context["park"]["resource_count"] = park_res.get("count")
        if "mcp_sqlite_db_query_policies" in tool_names:
            policies = self._call_json_tool(mcp_client, "mcp_sqlite_db_query_policies", {})
            if policies:
                context["park"]["policy_count"] = len(policies.get("policies", []))

        company = self._extract_company_candidate(user_input)
        if company:
            company_ctx = {"name": company}
            if "mcp_sqlite_db_query_crm_status" in tool_names:
                crm = self._call_json_tool(mcp_client, "mcp_sqlite_db_query_crm_status", {"company_name": company, "stage": "all"})
                records = crm.get("records", []) if isinstance(crm, dict) else []
                company_ctx["crm_found"] = bool(crm.get("found")) if isinstance(crm, dict) else False
                company_ctx["crm_stage_list"] = list({r.get("stage") for r in records if isinstance(r, dict) and r.get("stage")})
                company_ctx["is_signed"] = "已签约" in company_ctx.get("crm_stage_list", [])
            context["company"] = company_ctx

        lower = user_input.lower()
        context["intent"] = {
            "news": any(k in user_input for k in ["新闻", "动态", "资讯"]) or "news" in lower,
            "social_media": any(k in user_input for k in ["社交媒体", "微博", "公众号", "抖音"]) or any(k in lower for k in ["social", "twitter", "x.com", "linkedin"]),
            "park_ref": any(k in user_input for k in ["我们园区", "本园区", "园区"]),
        }
        return context

    def _rewrite_queries_with_llm(self, user_input: str, base_query: str, rewrite_context: Dict[str, Any]) -> List[str]:
        """让 LLM 结合园区上下文重写搜索词，返回主查询 + 备选查询。"""
        try:
            client = OpenAI(
                api_key=LLM_CONFIG["api_key"],
                base_url=LLM_CONFIG["api_base"],
                timeout=LLM_CONFIG.get("timeout", 45),
                max_retries=LLM_CONFIG.get("max_retries", 2),
            )
            context_text = json.dumps(rewrite_context, ensure_ascii=False)
            prompt = (
                '你是搜索词优化助手。请根据用户意图生成更适合搜索引擎检索的关键词，'
                '并结合已查询到的园区/企业上下文做实体消歧。\n\n'
                '规则：\n'
                '1) 若用户提到"我们园区/本园区"，优先映射到上下文里的 park_name\n'
                '2) 若提到某公司，结合 CRM 信息判断是否已入驻，并把身份加入查询词\n'
                '3) 若意图是社交媒体，查询词优先包含平台词\n'
                '4) 若意图是新闻，查询词优先包含"新闻/动态/通报"\n'
                '5) 保留用户的核心搜索意图，不要过度泛化\n\n'
                '要求：\n'
                '1) 输出 JSON，字段: primary_query, alt_queries\n'
                '2) primary_query 为最优检索词，尽量短且具体\n'
                '3) alt_queries 最多 4 条，去重，避免口语\n'
                '4) 不要输出任何解释文本\n\n'
                f'上下文数据：{context_text}\n'
                f'用户原始输入：{user_input}\n'
                f'初步清洗词：{base_query}\n'
            )
            resp = client.chat.completions.create(
                model=LLM_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "你只输出合法 JSON，不要 Markdown。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=256,
            )
            content = (resp.choices[0].message.content or "").strip()
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return [base_query] + self._build_fallback_queries(base_query)
            data = json.loads(content[start:end + 1])
            primary = str(data.get("primary_query", "")).strip()
            alts = data.get("alt_queries", [])
            if not isinstance(alts, list):
                alts = []
            candidates = [primary] + [str(x).strip() for x in alts]
            candidates.extend(self._build_fallback_queries(base_query))
            uniq = []
            seen = set()
            for q in candidates:
                if not q:
                    continue
                if q in seen:
                    continue
                seen.add(q)
                uniq.append(q)
            return uniq[:6] if uniq else [base_query]
        except Exception as e:
            logger.warning("[PlaywrightWebSearchSkill] LLM 查询改写失败，回退规则策略: %s", e)
            return [base_query] + self._build_fallback_queries(base_query)

    # ========== 核心新功能：自动点击进入搜索结果并抓取正文 ==========

    def _fetch_page_content(self, mcp_client: Any, url: str, names: set) -> Optional[str]:
        """导航到指定 URL 并提取页面正文内容"""
        try:
            mcp_client.call_tool("mcp_playwright_browser_navigate", {"url": url})

            # 等待页面加载
            if "mcp_playwright_browser_wait_for" in names:
                mcp_client.call_tool("mcp_playwright_browser_wait_for", {"time": 3})

            # 优先用 evaluate 提取正文
            if "mcp_playwright_browser_evaluate" in names:
                content = mcp_client.call_tool(
                    "mcp_playwright_browser_evaluate",
                    {
                        "function": (
                            "() => {"
                            "  function getText(sel) {"
                            "    const el = document.querySelector(sel);"
                            "    return el ? el.innerText.trim() : '';"
                            "  }"
                            # 常见正文容器选择器
                            "  const selectors = ["
                            "    'article', '.article-content', '.article-body',"
                            "    '.post-content', '.entry-content', '.content-text',"
                            "    '.news-content', '.detail-content', '#article',"
                            "    '[itemprop=\"articleBody\"]',"
                            "    'main', '.main-content', '#content', '.content'"
                            "  ];"
                            "  for (const sel of selectors) {"
                            "    const text = getText(sel);"
                            "    if (text && text.length > 100) {"
                            "      return text.slice(0, 3000);"
                            "    }"
                            "  }"
                            # 回退：取 body 的文本
                            "  const body = document.body ? document.body.innerText : '';"
                            "  return body ? body.slice(0, 3000) : '';"
                            "}"
                        )
                    }
                )
                text = self._extract_text_from_eval_result(content)
                if text and len(text) > 50:
                    return text[:MAX_CONTENT_CHARS]

            # 回退：用 snapshot 获取页面文本
            snapshot = mcp_client.call_tool("mcp_playwright_browser_snapshot", {})
            if snapshot:
                text = self._extract_text_from_snapshot(snapshot)
                if text and len(text) > 50:
                    return text[:MAX_CONTENT_CHARS]

            return None
        except Exception as e:
            logger.warning("[PlaywrightWebSearchSkill] 抓取页面内容失败 %s: %s", url, e)
            return None

    def _extract_text_from_eval_result(self, raw: str) -> str:
        """从 evaluate 结果中提取纯文本"""
        if not raw:
            return ""
        # 去掉 Playwright 返回的元数据部分
        result_part = raw
        marker = "### Result"
        if marker in raw:
            after = raw.split(marker, 1)[1]
            result_part = after.split("###", 1)[0].strip()

        # 尝试 JSON 字符串解码（Playwright 可能把文本包在 JSON 字符串里）
        try:
            parsed = json.loads(result_part)
            if isinstance(parsed, str):
                return parsed.strip()
        except Exception:
            pass

        # 去掉可能的引号包裹
        text = result_part.strip().strip('"').strip("'")
        return text

    def _extract_text_from_snapshot(self, snapshot: str) -> str:
        """从 snapshot 中提取可读文本（去掉元素标记等）"""
        if not snapshot:
            return ""
        lines = snapshot.splitlines()
        text_lines = []
        for line in lines:
            # 跳过 Playwright 元数据行
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- ") and any(
                kw in stripped[:30]
                for kw in ["link ", "button ", "img ", "navigation ", "banner ",
                           "textbox ", "checkbox ", "radio ", "combobox "]
            ):
                continue
            # 清理前缀标记
            clean = re.sub(r'^-\s*(text|heading|paragraph)\s*"?', '', stripped)
            clean = clean.strip().strip('"')
            if len(clean) > 5:
                text_lines.append(clean)
        return "\n".join(text_lines[:80])

    def _summarize_with_llm(self, query: str, items_with_content: List[Dict[str, str]]) -> str:
        """用 LLM 总结搜索结果和正文内容"""
        try:
            client = OpenAI(
                api_key=LLM_CONFIG["api_key"],
                base_url=LLM_CONFIG["api_base"],
                timeout=LLM_CONFIG.get("timeout", 45),
                max_retries=LLM_CONFIG.get("max_retries", 2),
            )

            # 构建内容摘要
            content_parts = []
            for idx, item in enumerate(items_with_content, start=1):
                title = item.get("title", "")
                url = item.get("url", "")
                content = item.get("content", "")
                part = f"【结果{idx}】{title}\nURL: {url}\n"
                if content:
                    part += f"正文摘要:\n{content}\n"
                else:
                    part += "（未能获取正文）\n"
                content_parts.append(part)

            all_content = "\n---\n".join(content_parts)

            resp = client.chat.completions.create(
                model=LLM_CONFIG["model"],
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一个信息总结助手。根据搜索到的网页内容，"
                            "为用户提供精准的信息摘要。如果内容中有与用户问题直接相关的答案，"
                            "请直接给出。如果都不太相关，诚实说明。"
                            "输出保持简洁，使用中文。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"用户搜索问题：{query}\n\n"
                            f"以下是搜索到的网页内容：\n\n{all_content}\n\n"
                            "请根据这些内容为用户总结相关信息。"
                        ),
                    },
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning("[PlaywrightWebSearchSkill] LLM 总结失败: %s", e)
            return ""

    # ========== 搜索结果提取（改进版） ==========

    def _extract_search_results_via_evaluate(self, mcp_client: Any, names: set) -> List[Dict[str, str]]:
        """通过 evaluate 在 Bing 搜索结果页提取链接（修复版过滤逻辑）"""
        if "mcp_playwright_browser_evaluate" not in names:
            return []

        eval_result = mcp_client.call_tool(
            "mcp_playwright_browser_evaluate",
            {
                "function": (
                    "() => {"
                    # 先精确选择 Bing 搜索结果的主要区域
                    "const selectors = ["
                    "  'li.b_algo h2 a',"
                    "  '#b_results h2 a',"
                    "  '.b_algo a[href]',"
                    "  'h2 a[href]',"
                    "  'h3 a[href]'"
                    "];"
                    "const out = [];"
                    "const seen = new Set();"
                    "for (const sel of selectors) {"
                    "  const anchors = document.querySelectorAll(sel);"
                    "  for (const a of anchors) {"
                    "    let href = (a.href || '').trim();"
                    "    const title = (a.innerText || a.textContent || '').trim().replace(/\\s+/g, ' ');"
                    "    if (!href.startsWith('http')) continue;"
                    "    if (!title || title.length < 4) continue;"
                    # 跳过搜索引擎内部页面和广告
                    "    if (href.includes('duckduckgo.com')) continue;"
                    "    if (href.includes('bing.com/images') || href.includes('bing.com/videos')) continue;"
                    "    if (href.includes('bing.com/maps') || href.includes('bing.com/aclick')) continue;"
                    "    if (href.includes('microsoftstart.com') || href.includes('go.microsoft.com')) continue;"
                    # Bing /ck/a 跳转链接是正常搜索结果，需保留
                    "    if (href.includes('bing.com') && !href.includes('/ck/a') && !href.includes('/news/') && !href.includes('url=')) continue;"
                    "    if (seen.has(href)) continue;"
                    "    seen.add(href);"
                    "    out.push({title: title.slice(0, 120), url: href});"
                    "    if (out.length >= 8) break;"
                    "  }"
                    "  if (out.length >= 8) break;"
                    "}"
                    "return JSON.stringify(out);"
                    "}"
                )
            }
        )
        return self._extract_items_from_eval_result(eval_result)

    def _format_items_response(self, query: str, items: List[Dict[str, str]], source: str,
                                summary: str = "") -> Dict[str, Any]:
        lines = []
        for idx, item in enumerate(items, start=1):
            title = (item.get("title") or "").strip()
            url = self._normalize_url((item.get("url") or "").strip())
            if not title or not url:
                continue
            lines.append(f"- {idx}. {title} | {url}")
        if not lines:
            return {}

        response = (
            f"✅ 已使用 Playwright 完成搜索：`{query}`\n\n"
            f"来源：{source}，检索到前 {len(lines)} 条结果：\n" + "\n".join(lines)
        )

        if summary:
            response += f"\n\n📝 **内容摘要**：\n{summary}"

        return {
            "handled": True,
            "response": response
        }

    # ========== 主执行流程 ==========

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_input = context.get("user_input", "")
        mcp_client = context.get("mcp_client")
        if not mcp_client:
            return {
                "handled": True,
                "response": "⚠️ 未检测到 MCP 客户端，无法执行网页搜索。"
            }

        try:
            all_tools = mcp_client.get_all_tools()
        except Exception as e:
            return {
                "handled": True,
                "response": f"⚠️ 获取工具列表失败: {e}"
            }

        names = self._get_tool_names(all_tools)
        required = {
            "mcp_playwright_browser_navigate",
            "mcp_playwright_browser_snapshot",
        }
        if not required.issubset(names):
            return {"handled": False}

        query = self._extract_query(user_input)
        rewrite_context = self._collect_rewrite_context(user_input, mcp_client, names)
        rewritten_queries = self._rewrite_queries_with_llm(user_input, query, rewrite_context)
        search_query = rewritten_queries[0]
        rss_queries = rewritten_queries

        try:
            # ── 阶段 1：优先使用 Bing News RSS 数据源 ──
            rss_items = []
            if "mcp_playwright_browser_evaluate" in names:
                mcp_client.call_tool("mcp_playwright_browser_navigate", {"url": "https://www.bing.com"})
                if "mcp_playwright_browser_wait_for" in names:
                    mcp_client.call_tool("mcp_playwright_browser_wait_for", {"time": 2})

                for rss_query in rss_queries:
                    rss_path = f"/news/search?q={urllib.parse.quote_plus(rss_query)}&format=rss"

                    rss_result = mcp_client.call_tool(
                        "mcp_playwright_browser_evaluate",
                        {
                            "function": (
                                "() => {"
                                f"const rssPath='{rss_path}';"
                                "return fetch(rssPath)"
                                ".then(r => r.text())"
                                ".then(xmlText => {"
                                "  const doc = new DOMParser().parseFromString(xmlText, 'text/xml');"
                                "  const nodes = [...doc.querySelectorAll('item')].slice(0,8);"
                                "  const items = nodes.map(i => ({"
                                "    title: (i.querySelector('title')?.textContent || '').trim(),"
                                "    url: (i.querySelector('link')?.textContent || '').trim()"
                                "  }));"
                                "  return JSON.stringify(items);"
                                "})"
                                ".catch(() => '[]');"
                                "}"
                            )
                        }
                    )
                    rss_items = self._extract_items_from_eval_result(rss_result)
                    if rss_items:
                        logger.info("[PlaywrightWebSearchSkill] RSS 命中 %d 条（查询: %s）", len(rss_items), rss_query)
                        break

            # ── 阶段 2：回退到常规搜索页面 ──
            web_items = []
            if not rss_items:
                search_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(search_query)}"
                mcp_client.call_tool("mcp_playwright_browser_navigate", {"url": search_url})
                if "mcp_playwright_browser_wait_for" in names:
                    mcp_client.call_tool("mcp_playwright_browser_wait_for", {"time": 3})

                # 优先用 evaluate 提取
                web_items = self._extract_search_results_via_evaluate(mcp_client, names)

                # 回退用 snapshot
                if not web_items:
                    snapshot = mcp_client.call_tool("mcp_playwright_browser_snapshot", {})
                    if self._is_bot_challenge(snapshot):
                        response = (
                            f"⚠️ 已打开搜索页，但被网站的人机验证拦截：`{search_query}`。\n\n"
                            "这不是业务流程 bug，属于搜索引擎反爬限制。"
                            "你可以重试一次，或使用更具体关键词；如果你本地可见浏览器窗口，先手动完成验证后再继续。"
                        )
                        return {"handled": True, "response": response}

                    web_items = self._extract_items_from_snapshot(snapshot)

                    # 最后一次尝试：用备选查询词重试
                    if not web_items and len(rewritten_queries) > 1:
                        for alt_query in rewritten_queries[1:3]:
                            alt_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(alt_query)}"
                            mcp_client.call_tool("mcp_playwright_browser_navigate", {"url": alt_url})
                            if "mcp_playwright_browser_wait_for" in names:
                                mcp_client.call_tool("mcp_playwright_browser_wait_for", {"time": 3})
                            web_items = self._extract_search_results_via_evaluate(mcp_client, names)
                            if web_items:
                                search_query = alt_query
                                break
                            snapshot = mcp_client.call_tool("mcp_playwright_browser_snapshot", {})
                            web_items = self._extract_items_from_snapshot(snapshot)
                            if web_items:
                                search_query = alt_query
                                break

            # ── 合并结果 ──
            all_items = rss_items or web_items
            source = "Bing News RSS" if rss_items else "Bing Web"

            if not all_items:
                response = (
                    f"✅ 已使用 Playwright 完成搜索：`{search_query}`\n\n"
                    '未能提取到有效结果链接。建议你换一个更具体的关键词（例如「光谷 园区 本周 招商 新闻」）。'
                )
                return {"handled": True, "response": response}

            # ── 阶段 3（核心新功能）：自动点击搜索结果，抓取正文 ──
            items_with_content = []
            pages_fetched = 0

            for item in all_items[:MAX_DETAIL_PAGES]:
                url = self._normalize_url(item.get("url", ""))
                if not url or not url.startswith("http"):
                    items_with_content.append(item)
                    continue

                logger.info("[PlaywrightWebSearchSkill] 正在抓取详情页: %s", url[:80])
                content = self._fetch_page_content(mcp_client, url, names)
                item_with_content = dict(item)
                if content:
                    item_with_content["content"] = content
                    pages_fetched += 1
                items_with_content.append(item_with_content)

            # 未抓取的结果也保留
            for item in all_items[MAX_DETAIL_PAGES:]:
                items_with_content.append(item)

            # ── 阶段 4：用 LLM 总结正文内容 ──
            summary = ""
            if pages_fetched > 0:
                summary = self._summarize_with_llm(
                    f"{user_input}（搜索词: {search_query}）",
                    items_with_content[:MAX_DETAIL_PAGES]
                )

            formatted = self._format_items_response(search_query, all_items, source, summary=summary)
            if formatted:
                return formatted

            # 理论上不会到这里
            return {
                "handled": True,
                "response": f"✅ 搜索完成（{search_query}），但未能格式化输出。"
            }

        except Exception as e:
            logger.warning("[PlaywrightWebSearchSkill] 搜索失败: %s", e)
            return {
                "handled": True,
                "response": f"❌ 使用 Playwright 搜索失败: {e}"
            }
