# -*- coding: utf-8 -*-
"""
125家模拟企业种子数据生成器
覆盖25个行业（包含5个前沿科技领域），每家企业有独特的特征组合
"""

# ============================================================
# 行业模板：定义每个行业的企业名称池和子行业
# ============================================================
INDUSTRY_TEMPLATES = {
    "半导体/集成电路": {
        "sub_industries": ["AI推理芯片", "FPGA设计", "模拟芯片", "封装测试", "EDA工具", "功率半导体", "存储芯片", "传感器芯片"],
        "names": ["未来芯片科技", "晶瑞微电子", "芯启源半导体", "中微达信", "锐芯微电子", "瀚天集成", "昊芯科技", "芯联达微"],
    },
    "人工智能": {
        "sub_industries": ["计算机视觉", "自然语言处理", "AI基础设施", "垂直行业AI", "机器人视觉", "AI安全", "大模型", "AI芯片算力"],
        "names": ["深思智能科技", "灵犀AI", "图灵数智", "认知智源", "博智天工", "星辰大模型", "慧眼识图", "智脑计算"],
    },
    "生物医药": {
        "sub_industries": ["创新药研发", "CRO/CDMO", "基因治疗", "医药AI", "中药现代化", "疫苗研发", "抗体药物"],
        "names": ["康瑞生物科技", "基因方舟", "瑞德制药", "免疫先锋", "华济药业", "分子诊断科技", "百奥源生物"],
    },
    "新能源汽车": {
        "sub_industries": ["整车制造", "电池管理系统", "电驱动系统", "智能座舱", "自动驾驶", "充电桩"],
        "names": ["逐光汽车", "绿驰智行", "电擎动力", "途远新能源", "智舱科技", "速充能源"],
    },
    "新能源/储能": {
        "sub_industries": ["锂电池", "氢能源", "光伏组件", "储能系统", "风电设备"],
        "names": ["聚能时代", "氢创未来", "阳光硅谷", "蓄力科技", "风行能源"],
    },
    "先进制造/智能制造": {
        "sub_industries": ["工业软件", "数字孪生", "工业机器人集成", "智能检测", "3D打印", "精密加工"],
        "names": ["智造未来", "数字工坊", "精研智能", "天工数控", "铸鑫精密", "迈拓增材"],
    },
    "医疗器械": {
        "sub_industries": ["体外诊断", "医学影像", "手术机器人", "可穿戴医疗", "植入物"],
        "names": ["锐影医疗", "微创达芬奇", "心脉医疗器械", "康复智能", "骨正医疗"],
    },
    "航空航天": {
        "sub_industries": ["卫星通信", "无人机", "航天材料", "发动机零部件"],
        "names": ["星途航天", "云翼无人机", "天合太空材料", "凌空动力"],
    },
    "新材料": {
        "sub_industries": ["碳纤维", "半导体材料", "功能涂层", "纳米材料", "高分子复合"],
        "names": ["碳纤未来", "硅基新材", "纳诺科技", "高分子创新", "镜面涂层"],
    },
    "金融科技": {
        "sub_industries": ["区块链", "智能风控", "数字支付", "保险科技"],
        "names": ["链信金融", "暴雷金融服务", "风盾智控", "普惠数科"],
    },
    "物联网/传感器": {
        "sub_industries": ["工业物联网", "智慧城市", "环境监测", "农业物联网", "车联网"],
        "names": ["万物智联", "城芯物联", "感知天下", "田间智控", "车路协同科技"],
    },
    "机器人": {
        "sub_industries": ["工业机器人", "服务机器人", "协作机器人", "特种机器人"],
        "names": ["灵巧机器人", "服务星球", "协力智能", "深海探索机器人"],
    },
    "大数据/云计算": {
        "sub_industries": ["数据中台", "云原生", "数据安全", "隐私计算", "边缘计算"],
        "names": ["数澜科技", "云原动力", "隐盾数据", "边际智算", "数据银河"],
    },
    "网络安全": {
        "sub_industries": ["零信任", "安全运营", "密码学", "威胁情报"],
        "names": ["盾甲安全", "零界信安", "密钥科技", "天盾威胁情报"],
    },
    "光电子/激光": {
        "sub_industries": ["光通信", "激光加工", "光学元件", "量子光学"],
        "names": ["光讯科技", "超快激光", "精微光学", "量子光源"],
    },
    "环保/节能": {
        "sub_industries": ["碳交易", "污水处理", "固废回收", "节能改造"],
        "names": ["碳中和科技", "清流环保", "循环再生", "绿建节能"],
    },
    "数字文创": {
        "sub_industries": ["游戏引擎", "VR/AR", "数字媒体"],
        "names": ["幻境科技", "虚实互动", "像素风暴"],
    },
    "现代农业科技": {
        "sub_industries": ["智慧种植", "农业AI", "生物育种"],
        "names": ["禾丰智农", "基因田园", "绿芯种业"],
    },
    "教育科技": {
        "sub_industries": ["AI教育", "职业培训平台", "教育硬件"],
        "names": ["智学星球", "技能工坊在线", "墨水屏教育"],
    },
    "跨境电商/供应链": {
        "sub_industries": ["跨境物流", "全球供应链SaaS"],
        "names": ["海途供应链", "全球链科技"],
    },
    # === 新增 5 个前沿行业 ===
    "量子科技": {
        "sub_industries": ["量子计算硬件", "量子通信", "量子测量", "量子算法软件"],
        "names": ["量子比特", "纠缠态科技", "超导量子云", "墨子通信"],
    },
    "合成生物学": {
        "sub_industries": ["基因编辑", "生物制造", "人造肉", "生物基材料"],
        "names": ["蓝晶微生物", "合成未来", "细胞工厂", "酶工程科技"],
    },
    "低空经济": {
        "sub_industries": ["eVTOL", "物流无人机", "低空空域管理", "航空器运维"],
        "names": ["飞翼出行", "天空物流", "低空智联网", "垂直起降动力"],
    },
    "脑科学与类脑智能": {
        "sub_industries": ["脑机接口", "神经调控", "类脑芯片", "脑疾病诊断"],
        "names": ["脑际接口", "神经元科技", "意念控制", "突触芯片"],
    },
    "生成式AI应用": {
        "sub_industries": ["AIGC内容生产", "数字人", "代码生成", "AI营销"],
        "names": ["妙笔生花", "数字分身", "代码副驾", "创意引擎"],
    },
}

# ============================================================
# 企业特征组合模板（用于生成多样化数据）
# ============================================================
FINANCING_STAGES = ["种子轮", "天使轮", "Pre-A轮", "A轮", "A+轮", "B轮", "B+轮", "C轮", "D轮", "Pre-IPO", "已上市"]

REVENUE_RANGES = [
    "未盈利", "0-500万", "500万-2000万", "2000万-5000万",
    "5000万-1亿", "1亿-3亿", "3亿-5亿", "5亿-10亿", "10亿以上"
]

REGIONS = ["武汉", "深圳", "北京", "上海", "杭州", "成都", "南京", "合肥", "广州", "苏州", "西安", "长沙"]

TAG_POOL = [
    "国家高新技术企业", "专精特新", "小巨人", "上市公司子公司",
    "外资企业", "军民融合", "瞪羚企业", "独角兽", "科技型中小企业",
    "知识产权优势企业", "双软认证", "ISO9001", "CMMI5", "院士工作站"
]

TEAM_BACKGROUNDS = [
    "核心团队来自华为、大疆等知名企业",
    "创始人为清华大学教授，带领多名博士创业",
    "连续创业团队，上一家公司已成功上市",
    "海归团队，核心技术源自斯坦福大学",
    "草根创业，从代工起步逐步转型自主研发",
    "从大型国企核心研发部门独立出来的团队",
    "互联网大厂中层管理者下海创业",
    "产学研合作，依托中科院技术成果转化",
    "政府招商引资重点引进的外地团队",
    "本地高校毕业生团队，深耕行业十年",
]


def generate_enterprises():
    """生成 ~125 家企业数据"""
    import random
    random.seed(42)  # 确保可重现

    enterprises = []
    ent_id = 1

    # 为每个行业生成企业
    for industry, template in INDUSTRY_TEMPLATES.items():
        # 每个行业生成 4-6 家企业
        names = template["names"]
        # 如果名字不够，稍微扩展一下
        count_to_gen = random.randint(6, 10)
        
        selected_names = []
        for i in range(count_to_gen):
            if i < len(names):
                base_name = names[i]
            else:
                base_name = names[i % len(names)] + str(i) # 简单的重名处理
            selected_names.append(base_name)

        for i, name in enumerate(selected_names):
            sub_ind = template["sub_industries"][i % len(template["sub_industries"])]
            stage_idx = random.randint(0, len(FINANCING_STAGES) - 1)
            stage = FINANCING_STAGES[stage_idx]

            # 员工数与阶段相关
            base_emp = {0: 8, 1: 15, 2: 25, 3: 50, 4: 80, 5: 120,
                        6: 180, 7: 300, 8: 500, 9: 800, 10: 2000}
            employees = base_emp.get(stage_idx, 100) + random.randint(-10, 100)
            employees = max(5, employees)

            # 营收与阶段相关
            rev_idx = min(stage_idx, len(REVENUE_RANGES) - 1)
            rev_idx = max(0, rev_idx + random.randint(-1, 1))
            revenue = REVENUE_RANGES[min(rev_idx, len(REVENUE_RANGES) - 1)]

            # 风险分数 - 大部分低风险，少部分高风险
            risk_weight = random.random()
            if risk_weight < 0.60:
                risk_score = random.randint(0, 20)    # 低风险
            elif risk_weight < 0.80:
                risk_score = random.randint(20, 40)   # 中等
            elif risk_weight < 0.92:
                risk_score = random.randint(40, 65)   # 关注
            else:
                risk_score = random.randint(65, 95)   # 高风险

            # 特殊高风险企业
            if "暴雷" in name:
                risk_score = random.randint(80, 95)

            # 标签
            n_tags = random.randint(0, 4)
            tags = random.sample(TAG_POOL, min(n_tags, len(TAG_POOL)))

            # 成立年份
            founded = random.randint(2010, 2025)

            # 地域
            region = random.choice(REGIONS)

            # 团队背景
            team = random.choice(TEAM_BACKGROUNDS)

            # 专利数
            patents = random.randint(0, 120)
            if stage_idx >= 7:
                patents += random.randint(20, 80)

            # 特殊特征
            special_traits = []
            trait_roll = random.random()
            if trait_roll < 0.08:
                special_traits.append("现金流严重不足，虽技术一流但濒临融资断裂")
                risk_score = max(risk_score, 45)
            elif trait_roll < 0.15:
                special_traits.append("高速增长，年营收翻3倍，但管理跟不上")
                risk_score = max(risk_score, 30)
            elif trait_roll < 0.20:
                special_traits.append("疑似空壳企业，注册资本虚高但无实质业务")
                risk_score = max(risk_score, 75)
            elif trait_roll < 0.25:
                special_traits.append("新三板退市企业，正在转型中")
                risk_score = max(risk_score, 40)
            elif trait_roll < 0.30:
                special_traits.append("与园区现有龙头企业有密切供应链关系")
            elif trait_roll < 0.35:
                special_traits.append("技术水平全国前三，但团队人员流失严重")
                risk_score = max(risk_score, 35)

            enterprise = {
                "id": f"ENT{ent_id:03d}",
                "name": name + "有限公司",
                "industry": industry,
                "sub_industry": sub_ind,
                "employees": employees,
                "financing_stage": stage,
                "revenue_range": revenue,
                "founded_year": founded,
                "region": region,
                "patents": patents,
                "tags": tags,
                "team_background": team,
                "special_traits": special_traits,
                "brief": "",  # 将在下面填充
            }

            # 生成简介
            enterprise["brief"] = _gen_brief(enterprise)

            enterprises.append(enterprise)
            ent_id += 1

    return enterprises


def _gen_brief(e):
    """根据企业属性自动拼接简介"""
    parts = [
        f"{e['name']}成立于{e['founded_year']}年，",
        f"位于{e['region']}，",
        f"是一家专注于{e['sub_industry']}领域的企业。",
        f"{e['team_background']}。",
        f"目前已完成{e['financing_stage']}融资，",
        f"员工规模约{e['employees']}人，",
        f"年营收{e['revenue_range']}。",
    ]
    if e["patents"] > 0:
        parts.append(f"已申请专利{e['patents']}项。")
    if e["tags"]:
        parts.append(f"获得{'/'.join(e['tags'][:3])}等资质。")
    if e["special_traits"]:
        parts.append(f"特别备注：{'; '.join(e['special_traits'])}。")
    return "".join(parts)


if __name__ == "__main__":
    data = generate_enterprises()
    print(f"共生成 {len(data)} 家企业，覆盖 {len(INDUSTRY_TEMPLATES)} 个行业")
