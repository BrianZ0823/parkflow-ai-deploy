# -*- coding: utf-8 -*-
"""园区资源种子数据"""

PARK_RESOURCES = [
    {"id": "PR001", "name": "A栋3层301室", "type": "office", "area_sqm": 200, "floor": 3,
     "rent_per_sqm": 45, "status": "空置", "facilities": "空调,网络,会议室共享", "decoration": "精装"},
    {"id": "PR002", "name": "A栋5层整层", "type": "office", "area_sqm": 800, "floor": 5,
     "rent_per_sqm": 42, "status": "空置", "facilities": "空调,网络,独立会议室,茶水间", "decoration": "精装"},
    {"id": "PR003", "name": "B栋1层标准厂房", "type": "factory", "area_sqm": 2000, "floor": 1,
     "rent_per_sqm": 25, "status": "空置", "facilities": "380V电力,行车,货梯", "decoration": "毛坯"},
    {"id": "PR004", "name": "B栋2层洁净车间", "type": "factory", "area_sqm": 1500, "floor": 2,
     "rent_per_sqm": 55, "status": "空置", "facilities": "万级洁净室,恒温恒湿,防静电", "decoration": "洁净装修"},
    {"id": "PR005", "name": "C栋共享实验室", "type": "lab", "area_sqm": 300, "floor": 1,
     "rent_per_sqm": 80, "status": "部分占用", "facilities": "生物安全柜,冷冻离心机,PCR仪", "decoration": "实验室标准"},
    {"id": "PR006", "name": "C栋化学分析实验室", "type": "lab", "area_sqm": 150, "floor": 2,
     "rent_per_sqm": 90, "status": "空置", "facilities": "通风橱,气相色谱,液相色谱", "decoration": "实验室标准"},
    {"id": "PR007", "name": "D栋1层大型厂房", "type": "factory", "area_sqm": 5000, "floor": 1,
     "rent_per_sqm": 20, "status": "空置", "facilities": "10吨行车,大型货梯,独立变电站", "decoration": "毛坯"},
    {"id": "PR008", "name": "A栋2层202室", "type": "office", "area_sqm": 120, "floor": 2,
     "rent_per_sqm": 48, "status": "空置", "facilities": "空调,网络", "decoration": "简装"},
    {"id": "PR009", "name": "E栋孵化空间", "type": "office", "area_sqm": 50, "floor": 3,
     "rent_per_sqm": 30, "status": "空置", "facilities": "共享工位,打印机,会议室", "decoration": "精装"},
    {"id": "PR010", "name": "F栋中试基地", "type": "lab", "area_sqm": 1000, "floor": 1,
     "rent_per_sqm": 60, "status": "空置", "facilities": "中试生产线,检测设备,仓储区", "decoration": "工业装修"},
]

PARK_POLICIES = [
    {"id": "POL001", "name": "光谷芯片企业专项补贴", "type": "产业补贴",
     "amount": "最高500万", "target": "半导体/集成电路", "condition": "年营收超2000万"},
    {"id": "POL002", "name": "高新技术企业入驻奖励", "type": "入驻奖励",
     "amount": "3年免租", "target": "国家高新技术企业", "condition": "持有高新技术企业证书"},
    {"id": "POL003", "name": "人才引进安家补贴", "type": "人才补贴",
     "amount": "博士30万/硕士10万", "target": "全行业", "condition": "全日制学历"},
    {"id": "POL004", "name": "光谷AI产业扶持计划", "type": "产业补贴",
     "amount": "最高300万", "target": "人工智能", "condition": "核心算法自主可控"},
    {"id": "POL005", "name": "生物医药研发费用补助", "type": "研发补助",
     "amount": "研发投入的20%（上限200万）", "target": "生物医药", "condition": "上年度研发投入超500万"},
    {"id": "POL006", "name": "专精特新企业奖励", "type": "资质奖励",
     "amount": "50万", "target": "全行业", "condition": "获得专精特新认定"},
]

PARK_INFO = {
    "name": "光谷智创园",
    "location": "武汉东湖高新区光谷大道77号",
    "total_area_sqm": 500000,
    "total_buildings": 12,
    "focus_industries": ["半导体与集成电路", "人工智能与大数据", "生物医药与大健康"],
    "established_year": 2018,
    "management_company": "武汉光谷智创园区管理有限公司",
}
