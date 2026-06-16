# -*- coding: utf-8 -*-
"""CRM 客户跟进记录种子数据"""

CRM_RECORDS = [
    # ===== 已签约企业 =====
    {
        "id": "CRM001", "company_name": "未来芯片科技有限公司",
        "contact_person": "张总", "contact_title": "VP of Operations",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-15", "expected_area": "2000㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-15", "note": "已入驻B栋2层，洁净车间改造完成，产线调试中"},
            {"date": "2025-10-08", "note": "签约3年租赁合同，享受高新企业免租政策"},
            {"date": "2025-09-20", "note": "对园区免租政策非常感兴趣，实地考察洁净车间后当场决定"},
        ]
    },
    {
        "id": "CRM002", "company_name": "深思智能科技有限公司",
        "contact_person": "王博士", "contact_title": "CEO",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-02-01", "expected_area": "500㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-02-01", "note": "入驻A栋5层，团队已全部搬迁完毕，正式运营"},
            {"date": "2025-12-15", "note": "签约2年合同，AI产业扶持计划审批通过"},
            {"date": "2025-11-10", "note": "参观园区后对算力中心非常满意"},
        ]
    },
    {
        "id": "CRM005", "company_name": "盾甲安全有限公司",
        "contact_person": "陈总", "contact_title": "COO",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-02-05", "expected_area": "300㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-02-05", "note": "已入驻A栋4层，运营良好，计划扩租"},
            {"date": "2025-11-20", "note": "签约3年租赁合同"},
        ]
    },
    {
        "id": "CRM008", "company_name": "晶瑞微电子有限公司",
        "contact_person": "黄工", "contact_title": "研发总监",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-20", "expected_area": "600㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-20", "note": "FPGA设计团队已全部入驻A栋3层，设备搬迁完毕"},
            {"date": "2025-09-15", "note": "签约2年合同，享受半导体专项补贴"},
        ]
    },
    {
        "id": "CRM009", "company_name": "灵犀AI有限公司",
        "contact_person": "周总", "contact_title": "CTO",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-28", "expected_area": "350㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-28", "note": "NLP团队入驻E栋3层孵化空间，准备扩展到整层"},
            {"date": "2025-10-25", "note": "签约1年合同，正在申请AI产业扶持计划"},
        ]
    },
    {
        "id": "CRM010", "company_name": "基因方舟有限公司",
        "contact_person": "吴教授", "contact_title": "首席科学家",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-02-03", "expected_area": "400㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-02-03", "note": "已入驻C栋共享实验室，基因编辑平台已投入使用"},
            {"date": "2025-08-20", "note": "签约3年合同，生物医药研发补助已到账"},
        ]
    },
    {
        "id": "CRM011", "company_name": "聚能时代有限公司",
        "contact_person": "马总", "contact_title": "总经理",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2025-12-18", "expected_area": "1200㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-12-18", "note": "入驻B栋1层标准厂房，锂电池测试产线部署中"},
            {"date": "2025-07-10", "note": "签约5年合同，电力增容方案已落实"},
        ]
    },
    {
        "id": "CRM012", "company_name": "数澜科技有限公司",
        "contact_person": "林总", "contact_title": "VP",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-06", "expected_area": "280㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-06", "note": "入驻A栋2层，数据中台团队运转正常"},
            {"date": "2025-09-01", "note": "签约2年合同"},
        ]
    },
    {
        "id": "CRM013", "company_name": "万物智联有限公司",
        "contact_person": "韩总", "contact_title": "CEO",
        "stage": "已签约", "interest_level": "中",
        "last_contact": "2025-11-30", "expected_area": "200㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-11-30", "note": "IoT硬件实验室已搭建完成，入驻E栋"},
            {"date": "2025-06-20", "note": "签约2年合同"},
        ]
    },
    {
        "id": "CRM014", "company_name": "锐影医疗有限公司",
        "contact_person": "郑总", "contact_title": "总经理",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-12", "expected_area": "500㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-12", "note": "医学影像设备已安装调试，入驻C栋2层"},
            {"date": "2025-08-05", "note": "签约3年合同，GMP实验室改造完成"},
        ]
    },
    {
        "id": "CRM015", "company_name": "智造未来有限公司",
        "contact_person": "曹工", "contact_title": "技术VP",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2025-12-22", "expected_area": "800㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-12-22", "note": "工业软件团队入驻A栋6层，数字孪生平台上线"},
            {"date": "2025-07-18", "note": "签约3年合同"},
        ]
    },
    {
        "id": "CRM016", "company_name": "星途航天有限公司",
        "contact_person": "钱总", "contact_title": "副总裁",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2025-12-10", "expected_area": "1000㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-12-10", "note": "卫星通信实验室部署完成，入驻D栋"},
            {"date": "2025-06-01", "note": "签约5年合同，政府军民融合专项支持"},
        ]
    },
    {
        "id": "CRM017", "company_name": "碳纤未来有限公司",
        "contact_person": "孟总", "contact_title": "总经理",
        "stage": "已签约", "interest_level": "中",
        "last_contact": "2025-11-15", "expected_area": "1500㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-11-15", "note": "中试产线入驻F栋中试基地，碳纤维样品已出"},
            {"date": "2025-05-20", "note": "签约3年合同"},
        ]
    },
    {
        "id": "CRM018", "company_name": "灵巧机器人有限公司",
        "contact_person": "沈博士", "contact_title": "首席科学家",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-08", "expected_area": "400㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-08", "note": "工业机器人调试区搭建完成，A栋1层"},
            {"date": "2025-08-12", "note": "签约2年合同"},
        ]
    },
    {
        "id": "CRM019", "company_name": "链信金融有限公司",
        "contact_person": "杨总", "contact_title": "COO",
        "stage": "已签约", "interest_level": "中",
        "last_contact": "2025-10-20", "expected_area": "250㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-10-20", "note": "区块链研发中心入驻A栋3层"},
            {"date": "2025-05-15", "note": "签约2年合同"},
        ]
    },
    {
        "id": "CRM020", "company_name": "光讯科技有限公司",
        "contact_person": "刘工", "contact_title": "技术总监",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-20", "expected_area": "400㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-20", "note": "光通信实验室入驻B栋3层，与周边光电企业合作顺利"},
            {"date": "2025-09-05", "note": "签约3年合同，光电子行业集聚效应是决定因素"},
        ]
    },
    {
        "id": "CRM021", "company_name": "零界信安有限公司",
        "contact_person": "唐总", "contact_title": "CEO",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2025-12-28", "expected_area": "200㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-12-28", "note": "零信任安全产品研发团队入驻E栋"},
            {"date": "2025-07-22", "note": "签约2年合同"},
        ]
    },
    {
        "id": "CRM022", "company_name": "图灵数智有限公司",
        "contact_person": "方博士", "contact_title": "联合创始人",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-18", "expected_area": "300㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-18", "note": "AI基础设施团队入驻，已使用园区算力池服务"},
            {"date": "2025-10-10", "note": "签约2年合同，算力支持是主要吸引点"},
        ]
    },
    {
        "id": "CRM023", "company_name": "瑞德制药有限公司",
        "contact_person": "许总", "contact_title": "研发总监",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-02-06", "expected_area": "600㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-02-06", "note": "入驻C栋实验室，GMP车间正在装修，预计Q2投入使用"},
            {"date": "2025-09-25", "note": "签约5年合同，享受生物医药研发补助"},
        ]
    },
    {
        "id": "CRM024", "company_name": "电擎动力有限公司",
        "contact_person": "龚总", "contact_title": "总工程师",
        "stage": "已签约", "interest_level": "中",
        "last_contact": "2025-11-28", "expected_area": "800㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-11-28", "note": "电驱动系统测试实验室入驻D栋1层"},
            {"date": "2025-06-15", "note": "签约3年合同"},
        ]
    },
    {
        "id": "CRM025", "company_name": "幻境科技有限公司",
        "contact_person": "范总", "contact_title": "创始人",
        "stage": "已签约", "interest_level": "中",
        "last_contact": "2025-10-30", "expected_area": "180㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-10-30", "note": "VR/AR研发团队入驻E栋孵化空间"},
            {"date": "2025-05-08", "note": "签约1年合同"},
        ]
    },
    {
        "id": "CRM026", "company_name": "感知天下有限公司",
        "contact_person": "贺总", "contact_title": "副总经理",
        "stage": "已签约", "interest_level": "中",
        "last_contact": "2025-12-05", "expected_area": "350㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-12-05", "note": "环境监测传感器测试中心入驻B栋"},
            {"date": "2025-06-28", "note": "签约2年合同"},
        ]
    },
    {
        "id": "CRM027", "company_name": "禾丰智农有限公司",
        "contact_person": "蔡总", "contact_title": "CEO",
        "stage": "已签约", "interest_level": "中",
        "last_contact": "2025-11-22", "expected_area": "150㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2025-11-22", "note": "智慧农业AI算法团队入驻A栋"},
            {"date": "2025-06-10", "note": "签约2年合同"},
        ]
    },
    {
        "id": "CRM028", "company_name": "量子比特有限公司",
        "contact_person": "潘教授", "contact_title": "首席科学家",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-25", "expected_area": "500㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-25", "note": "量子计算实验室入驻C栋，低温制冷设备安装完成"},
            {"date": "2025-07-01", "note": "签约5年合同，政府战略性新兴产业专项支持"},
        ]
    },
    {
        "id": "CRM029", "company_name": "蓝晶微生物有限公司",
        "contact_person": "谢总", "contact_title": "总经理",
        "stage": "已签约", "interest_level": "高",
        "last_contact": "2026-01-30", "expected_area": "800㎡",
        "expected_move_in": "已入驻",
        "notes": [
            {"date": "2026-01-30", "note": "入驻F栋中试基地，发酵车间改造进行中"},
            {"date": "2025-08-18", "note": "签约3年合同，合成生物学方向重点扶持"},
        ]
    },

    # ===== 意向明确 =====
    {
        "id": "CRM030", "company_name": "芯启源半导体有限公司",
        "contact_person": "秦总", "contact_title": "CEO",
        "stage": "意向明确", "interest_level": "高",
        "last_contact": "2026-02-08", "expected_area": "1200㎡",
        "expected_move_in": "2026-Q2",
        "notes": [
            {"date": "2026-02-08", "note": "已参观洁净车间，对封测产线场地非常满意，正在走内部审批"},
            {"date": "2026-01-15", "note": "二次考察，带技术团队评估设备搬迁方案"},
            {"date": "2025-12-20", "note": "首次参观，对半导体专项补贴很感兴趣"},
        ]
    },
    {
        "id": "CRM031", "company_name": "认知智源有限公司",
        "contact_person": "田总", "contact_title": "CTO",
        "stage": "意向明确", "interest_level": "高",
        "last_contact": "2026-02-06", "expected_area": "400㎡",
        "expected_move_in": "2026-Q2",
        "notes": [
            {"date": "2026-02-06", "note": "已提交入驻申请，等待集团最终审批"},
            {"date": "2026-01-20", "note": "对园区算力池服务非常认可，垂直行业AI方向"},
        ]
    },
    {
        "id": "CRM032", "company_name": "飞翼出行有限公司",
        "contact_person": "邓总", "contact_title": "战略总监",
        "stage": "意向明确", "interest_level": "高",
        "last_contact": "2026-02-09", "expected_area": "2000㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-02-09", "note": "eVTOL试飞基地选址考察，对D栋大型厂房有强烈意向"},
            {"date": "2026-01-28", "note": "与园区管理层面谈，讨论低空经济产业专项政策"},
        ]
    },
    {
        "id": "CRM033", "company_name": "妙笔生花有限公司",
        "contact_person": "叶总", "contact_title": "联合创始人",
        "stage": "意向明确", "interest_level": "高",
        "last_contact": "2026-02-07", "expected_area": "300㎡",
        "expected_move_in": "2026-Q2",
        "notes": [
            {"date": "2026-02-07", "note": "AIGC内容生成团队计划从北京搬迁，武汉人力成本优势明显"},
            {"date": "2026-01-18", "note": "远程考察园区，对人才公寓配套很满意"},
        ]
    },
    {
        "id": "CRM034", "company_name": "免疫先锋有限公司",
        "contact_person": "丁教授", "contact_title": "CEO",
        "stage": "意向明确", "interest_level": "高",
        "last_contact": "2026-02-04", "expected_area": "600㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-02-04", "note": "抗体药物研发所需的GMP实验室已进入合同细节谈判阶段"},
            {"date": "2026-01-10", "note": "实地考察C栋实验室，对生物安全设施满意"},
        ]
    },
    {
        "id": "CRM035", "company_name": "纳诺科技有限公司",
        "contact_person": "任总", "contact_title": "总经理",
        "stage": "意向明确", "interest_level": "中",
        "last_contact": "2026-01-30", "expected_area": "500㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-01-30", "note": "纳米材料中试生产需要F栋中试基地，正在评估场地"},
            {"date": "2025-12-15", "note": "首次考察，对新材料产业配套感兴趣"},
        ]
    },

    # ===== 洽谈中 =====
    {
        "id": "CRM036", "company_name": "康瑞生物科技有限公司",
        "contact_person": "李总", "contact_title": "CFO",
        "stage": "洽谈中", "interest_level": "中",
        "last_contact": "2026-01-28", "expected_area": "800㎡",
        "expected_move_in": "2026-Q4",
        "notes": [
            {"date": "2026-01-28", "note": "关注实验室资源，询问是否有GMP级别车间"},
            {"date": "2025-12-10", "note": "CFO来访，主要关心租金和政策优惠力度"},
        ]
    },
    {
        "id": "CRM037", "company_name": "云原动力有限公司",
        "contact_person": "宋总", "contact_title": "技术VP",
        "stage": "洽谈中", "interest_level": "高",
        "last_contact": "2026-02-03", "expected_area": "350㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-02-03", "note": "云原生平台团队扩张，正在比较光谷和武汉经开区两个园区"},
            {"date": "2026-01-12", "note": "技术负责人来访，关注网络带宽和IDC资源"},
        ]
    },
    {
        "id": "CRM038", "company_name": "脑际接口有限公司",
        "contact_person": "陆博士", "contact_title": "首席科学家",
        "stage": "洽谈中", "interest_level": "高",
        "last_contact": "2026-02-05", "expected_area": "400㎡",
        "expected_move_in": "2026-Q4",
        "notes": [
            {"date": "2026-02-05", "note": "脑机接口实验室对洁净度和电磁屏蔽有特殊要求，需评估改造方案"},
            {"date": "2026-01-08", "note": "创始人来访，技术源自华中科技大学同济医学院"},
        ]
    },
    {
        "id": "CRM039", "company_name": "精研智能有限公司",
        "contact_person": "吕总", "contact_title": "总工程师",
        "stage": "洽谈中", "interest_level": "中",
        "last_contact": "2026-01-25", "expected_area": "600㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-01-25", "note": "智能检测设备展厅和测试中心选址中"},
            {"date": "2025-12-20", "note": "通过行业展会了解到园区，对智能制造产业集群感兴趣"},
        ]
    },
    {
        "id": "CRM040", "company_name": "氢创未来有限公司",
        "contact_person": "汪总", "contact_title": "CEO",
        "stage": "洽谈中", "interest_level": "中",
        "last_contact": "2026-01-22", "expected_area": "1500㎡",
        "expected_move_in": "2027-Q1",
        "notes": [
            {"date": "2026-01-22", "note": "氢能源研发实验室需要特殊安全设施，园区正在评估可行性"},
            {"date": "2025-11-30", "note": "初次接洽，对新能源产业政策有兴趣"},
        ]
    },
    {
        "id": "CRM041", "company_name": "超快激光有限公司",
        "contact_person": "习总", "contact_title": "副总经理",
        "stage": "洽谈中", "interest_level": "高",
        "last_contact": "2026-02-01", "expected_area": "500㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-02-01", "note": "激光加工设备需要大功率电力支持，正在核算电力增容成本"},
            {"date": "2026-01-05", "note": "武汉光电子产业基础吸引了该企业的关注"},
        ]
    },
    {
        "id": "CRM042", "company_name": "数字分身有限公司",
        "contact_person": "魏总", "contact_title": "CEO",
        "stage": "洽谈中", "interest_level": "高",
        "last_contact": "2026-02-08", "expected_area": "250㎡",
        "expected_move_in": "2026-Q2",
        "notes": [
            {"date": "2026-02-08", "note": "数字人技术团队从上海搬迁，看中武汉AI产业氛围"},
            {"date": "2026-01-20", "note": "线上沟通，对园区算力池和人才公寓很感兴趣"},
        ]
    },
    {
        "id": "CRM043", "company_name": "硅基新材有限公司",
        "contact_person": "崔总", "contact_title": "总经理",
        "stage": "洽谈中", "interest_level": "中",
        "last_contact": "2026-01-18", "expected_area": "1000㎡",
        "expected_move_in": "2026-Q4",
        "notes": [
            {"date": "2026-01-18", "note": "半导体材料中试产线需要洁净车间和化学品存储设施"},
            {"date": "2025-12-05", "note": "通过半导体行业协会推荐了解到园区"},
        ]
    },

    # ===== 初步接触 =====
    {
        "id": "CRM044", "company_name": "碳中和科技有限公司",
        "contact_person": "孙总", "contact_title": "CEO",
        "stage": "初步接触", "interest_level": "中",
        "last_contact": "2026-02-08", "expected_area": "200㎡",
        "expected_move_in": "待定",
        "notes": [
            {"date": "2026-02-08", "note": "在碳交易论坛上结识，对ESG方面政策感兴趣"},
        ]
    },
    {
        "id": "CRM045", "company_name": "天空物流有限公司",
        "contact_person": "高总", "contact_title": "运营总监",
        "stage": "初步接触", "interest_level": "中",
        "last_contact": "2026-02-06", "expected_area": "待定",
        "expected_move_in": "待定",
        "notes": [
            {"date": "2026-02-06", "note": "物流无人机运营公司，正在多个城市布局节点"},
        ]
    },
    {
        "id": "CRM046", "company_name": "代码副驾有限公司",
        "contact_person": "夏总", "contact_title": "创始人",
        "stage": "初步接触", "interest_level": "高",
        "last_contact": "2026-02-09", "expected_area": "200㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-02-09", "note": "AI代码生成创业团队，YC毕业项目，看中武汉华科大计算机人才"},
        ]
    },
    {
        "id": "CRM047", "company_name": "细胞工厂有限公司",
        "contact_person": "姚博士", "contact_title": "CTO",
        "stage": "初步接触", "interest_level": "中",
        "last_contact": "2026-01-28", "expected_area": "500㎡",
        "expected_move_in": "待定",
        "notes": [
            {"date": "2026-01-28", "note": "人造肉制造技术团队，需要发酵车间和食品级洁净室"},
        ]
    },
    {
        "id": "CRM048", "company_name": "深海探索机器人有限公司",
        "contact_person": "姜总", "contact_title": "总经理",
        "stage": "初步接触", "interest_level": "低",
        "last_contact": "2026-01-20", "expected_area": "待定",
        "expected_move_in": "待定",
        "notes": [
            {"date": "2026-01-20", "note": "特种机器人企业，深圳总部，武汉仅考虑设立销售办公室"},
        ]
    },
    {
        "id": "CRM049", "company_name": "边际智算有限公司",
        "contact_person": "彭总", "contact_title": "VP",
        "stage": "初步接触", "interest_level": "高",
        "last_contact": "2026-02-07", "expected_area": "300㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-02-07", "note": "边缘计算公司，希望在园区部署边缘节点，正在评估网络条件"},
        ]
    },
    {
        "id": "CRM050", "company_name": "突触芯片有限公司",
        "contact_person": "梁博士", "contact_title": "首席科学家",
        "stage": "初步接触", "interest_level": "高",
        "last_contact": "2026-02-10", "expected_area": "400㎡",
        "expected_move_in": "2026-Q4",
        "notes": [
            {"date": "2026-02-10", "note": "类脑芯片初创企业，从中科院神经所孵化，正在全国选址"},
        ]
    },
    {
        "id": "CRM051", "company_name": "绿驰智行有限公司",
        "contact_person": "贾总", "contact_title": "战略总监",
        "stage": "初步接触", "interest_level": "中",
        "last_contact": "2026-01-15", "expected_area": "1200㎡",
        "expected_move_in": "待定",
        "notes": [
            {"date": "2026-01-15", "note": "新能源汽车电池管理系统研发，目前在合肥，考虑武汉设分中心"},
        ]
    },
    {
        "id": "CRM052", "company_name": "服务星球有限公司",
        "contact_person": "谭总", "contact_title": "CEO",
        "stage": "初步接触", "interest_level": "中",
        "last_contact": "2026-02-03", "expected_area": "250㎡",
        "expected_move_in": "2026-Q3",
        "notes": [
            {"date": "2026-02-03", "note": "服务机器人公司，在酒店和医院场景已有落地，寻找华中区展示中心"},
        ]
    },

    # ===== 已流失 =====
    {
        "id": "CRM053", "company_name": "逐光汽车有限公司",
        "contact_person": "赵总", "contact_title": "战略总监",
        "stage": "已流失", "interest_level": "低",
        "last_contact": "2025-09-15", "expected_area": "5000㎡",
        "expected_move_in": "N/A",
        "notes": [
            {"date": "2025-09-15", "note": "最终选择了合肥的园区，因为更接近供应链"},
            {"date": "2025-08-01", "note": "需要大型厂房用于整车测试"},
        ]
    },
    {
        "id": "CRM054", "company_name": "海途供应链有限公司",
        "contact_person": "程总", "contact_title": "CEO",
        "stage": "已流失", "interest_level": "低",
        "last_contact": "2025-08-20", "expected_area": "300㎡",
        "expected_move_in": "N/A",
        "notes": [
            {"date": "2025-08-20", "note": "跨境电商物流业务需要靠近港口，武汉不满足需求，转向宁波"},
        ]
    },
    {
        "id": "CRM055", "company_name": "全球链科技有限公司",
        "contact_person": "侯总", "contact_title": "VP",
        "stage": "已流失", "interest_level": "低",
        "last_contact": "2025-07-10", "expected_area": "200㎡",
        "expected_move_in": "N/A",
        "notes": [
            {"date": "2025-07-10", "note": "供应链SaaS公司放弃武汉，选择深圳前海自贸区"},
        ]
    },
    {
        "id": "CRM056", "company_name": "风行能源有限公司",
        "contact_person": "冯总", "contact_title": "总工",
        "stage": "已流失", "interest_level": "低",
        "last_contact": "2025-10-05", "expected_area": "3000㎡",
        "expected_move_in": "N/A",
        "notes": [
            {"date": "2025-10-05", "note": "风电设备企业需要大面积户外测试场地，园区无法满足"},
        ]
    },
]
