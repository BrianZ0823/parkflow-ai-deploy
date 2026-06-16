# -*- coding: utf-8 -*-
"""7 个 MCP 工具的 OpenAI Function Calling Schema 定义"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_enterprises",
            "description": "从OPC企业池（招商候选目标库）中检索潜在招商目标企业。注意：这里搜索的是候选目标，不是已入驻企业。查已入驻企业请用query_crm_status(stage='已签约')。",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {"type": "string", "description": "行业关键词，如'半导体'、'人工智能'、'生物医药'"},
                    "min_employees": {"type": "integer", "description": "最小员工数"},
                    "max_employees": {"type": "integer", "description": "最大员工数"},
                    "financing_stage": {"type": "string", "description": "融资阶段：'天使轮','A轮','B轮','C轮','D轮','Pre-IPO','已上市'"},
                    "region": {"type": "string", "description": "企业所在区域，如'武汉','深圳','北京'"},
                    "tags": {"type": "string", "description": "企业标签，如'专精特新','国家高新技术企业'"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_risk",
            "description": "查询企业风险评分，包括诉讼记录、负面舆情、风险标签。risk_score>60为高风险。",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "企业名称（全称或关键字）"},
                },
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_industry_chain",
            "description": "在产业链知识图谱中查询产业上下游关系、园区缺口分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {"type": "string", "description": "行业名称，如'半导体/集成电路'"},
                    "query_type": {
                        "type": "string",
                        "enum": ["full_chain", "upstream", "downstream", "gap_analysis"],
                        "description": "查询类型：full_chain(完整上下游), upstream(仅上游), downstream(仅下游), gap_analysis(园区缺口分析)",
                    },
                },
                "required": ["industry"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_park_resources",
            "description": "查询园区可用的办公室、厂房、实验室等资源，以及园区优惠政策。",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_type": {"type": "string", "enum": ["office", "factory", "lab", "all"], "description": "资源类型"},
                    "min_area": {"type": "number", "description": "最小面积（平方米）"},
                    "max_rent": {"type": "number", "description": "最高租金（元/平方米/月）"},
                    "include_policies": {"type": "boolean", "description": "是否同时返回相关优惠政策"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_crm_status",
            "description": "查询CRM客户跟进状态。可按企业名称模糊搜索或按阶段筛选。stage='已签约'即为已入驻企业。",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "企业名称（支持模糊匹配）"},
                    "stage": {"type": "string", "enum": ["初步接触", "洽谈中", "意向明确", "已签约", "已流失", "all"], "description": "跟进阶段筛选"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "在向量知识库中语义检索企业画像、招商手册、行业报告、政策文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索语义关键词或问题"},
                    "collection": {
                        "type": "string",
                        "enum": ["company_profiles", "park_brochures", "industry_reports", "policy_summaries", "all"],
                        "description": "检索的集合：company_profiles(企业画像), park_brochures(招商手册), industry_reports(行业报告), policy_summaries(政策摘要), all(全部)",
                    },
                    "top_k": {"type": "integer", "description": "返回结果数量，默认3"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_external_intelligence",
            "description": "查询企业工商信息、股权结构、专利、融资历史等外部情报。",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "企业名称（全称或关键字）"},
                    "info_type": {
                        "type": "string",
                        "enum": ["basic", "shareholders", "patents", "financing", "all"],
                        "description": "查询类型",
                    },
                },
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期、时间、星期等信息。当用户询问今天日期、现在几点、星期几等时间相关问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "时区，默认为 Asia/Shanghai，如'UTC','America/New_York'"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_crm_record",
            "description": "更新CRM客户跟进记录。可修改企业跟进阶段、添加跟进备注、设置下次跟进日期。更新后会返回变更详情。",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "企业名称（支持模糊匹配）"},
                    "new_stage": {
                        "type": "string",
                        "enum": ["初步接触", "洽谈中", "意向明确", "已签约", "已流失"],
                        "description": "新的跟进阶段",
                    },
                    "follow_up_note": {"type": "string", "description": "跟进备注，如会议纪要、沟通要点等"},
                    "next_follow_up_date": {"type": "string", "description": "下次跟进日期，格式：YYYY-MM-DD"},
                },
                "required": ["company_name"],
            },
        },
    },
]
