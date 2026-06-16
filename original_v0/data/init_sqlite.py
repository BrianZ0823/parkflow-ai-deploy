# -*- coding: utf-8 -*-
"""初始化 SQLite 数据库：企业池 + 园区资源 + CRM"""
import sqlite3
import json
import os
import sys

# 将项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DB_PATH = os.path.join(PROJECT_ROOT, "db", "park_data.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ---------- 企业表 ----------
    c.execute("DROP TABLE IF EXISTS enterprises")
    c.execute("""
        CREATE TABLE enterprises (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT,
            sub_industry TEXT,
            employees INTEGER,
            financing_stage TEXT,
            revenue_range TEXT,
            founded_year INTEGER,
            region TEXT,
            patents INTEGER DEFAULT 0,
            tags TEXT,          -- JSON array
            team_background TEXT,
            special_traits TEXT, -- JSON array
            brief TEXT,
            risk_score INTEGER DEFAULT 0
        )
    """)

    # ---------- 园区资源表 ----------
    c.execute("DROP TABLE IF EXISTS park_resources")
    c.execute("""
        CREATE TABLE park_resources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            area_sqm REAL,
            floor INTEGER,
            rent_per_sqm REAL,
            status TEXT,
            facilities TEXT,
            decoration TEXT
        )
    """)

    # ---------- 园区政策表 ----------
    c.execute("DROP TABLE IF EXISTS park_policies")
    c.execute("""
        CREATE TABLE park_policies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            amount TEXT,
            target TEXT,
            condition TEXT
        )
    """)

    # ---------- CRM 表 ----------
    c.execute("DROP TABLE IF EXISTS crm_records")
    c.execute("""
        CREATE TABLE crm_records (
            id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            contact_person TEXT,
            contact_title TEXT,
            stage TEXT,
            interest_level TEXT,
            last_contact TEXT,
            expected_area TEXT,
            expected_move_in TEXT,
            notes TEXT,  -- JSON array
            next_follow_up TEXT  -- 下次跟进日期
        )
    """)

    # ---------- 灌入数据 ----------
    from data.seed_data.enterprises import generate_enterprises
    from data.seed_data.park_resources import PARK_RESOURCES, PARK_POLICIES
    from data.seed_data.crm_records import CRM_RECORDS

    enterprises = generate_enterprises()
    for e in enterprises:
        c.execute("""
            INSERT INTO enterprises VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            e["id"], e["name"], e["industry"], e["sub_industry"],
            e["employees"], e["financing_stage"], e["revenue_range"],
            e["founded_year"], e["region"], e["patents"],
            json.dumps(e["tags"], ensure_ascii=False),
            e["team_background"],
            json.dumps(e["special_traits"], ensure_ascii=False),
            e["brief"],
            e.get("risk_score", 0),
        ))

    for r in PARK_RESOURCES:
        c.execute("INSERT INTO park_resources VALUES (?,?,?,?,?,?,?,?,?)", (
            r["id"], r["name"], r["type"], r["area_sqm"], r["floor"],
            r["rent_per_sqm"], r["status"], r["facilities"], r["decoration"],
        ))

    for p in PARK_POLICIES:
        c.execute("INSERT INTO park_policies VALUES (?,?,?,?,?,?)", (
            p["id"], p["name"], p["type"], p["amount"], p["target"], p["condition"],
        ))

    import random
    random.seed(42)
    
    # === 补全已入驻企业至目标数量 ===
    CONTACT_SURNAMES = ["张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴",
                        "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "罗", "高"]
    CONTACT_TITLES = ["总经理", "CEO", "CTO", "COO", "总工程师", "VP",
                      "运营总监", "副总裁", "技术总监", "研发总监", "董事长"]
    BUILDINGS = ["A栋", "B栋", "C栋", "D栋", "E栋", "F栋"]
    FLOORS = ["1层", "2层", "3层", "4层", "5层", "6层"]
    CONTRACT_YEARS = ["1年", "2年", "3年", "5年"]
    BUSINESS_NOTES = [
        "团队入驻运转正常，已与园区内多家企业建立合作",
        "研发产线部署完毕，正式投入运营",
        "入驻以来业务发展良好，正在考虑扩租",
        "办公区装修完成，首批员工已入驻",
        "实验室搭建完毕，研发项目按计划推进",
        "入驻后积极参与园区产业对接活动",
        "已完成设备搬迁安装，开始正式运营",
        "团队融入园区氛围良好，和邻近企业有技术交流",
    ]
    
    existing_signed = sum(1 for r in CRM_RECORDS if r["stage"] == "已签约")
    target_signed = 60
    
    if existing_signed < target_signed:
        needed = target_signed - existing_signed
        crm_companies = {r["company_name"] for r in CRM_RECORDS}
        available_ents = [e for e in enterprises if e["name"] not in crm_companies]
        
        to_add = random.sample(available_ents, min(needed, len(available_ents)))
        
        for i, ent in enumerate(to_add):
            surname = random.choice(CONTACT_SURNAMES)
            title = random.choice(CONTACT_TITLES)
            building = random.choice(BUILDINGS)
            floor = random.choice(FLOORS)
            contract = random.choice(CONTRACT_YEARS)
            note = random.choice(BUSINESS_NOTES)
            # 随机日期 (2025-06 ~ 2026-02)
            month = random.randint(6, 14)
            year = 2025 if month <= 12 else 2026
            real_month = month if month <= 12 else month - 12
            day = random.randint(1, 28)
            sign_date = f"{year}-{real_month:02d}-{day:02d}"
            lc_month = min(real_month + random.randint(1, 3), 12) if year == 2025 else min(real_month + random.randint(0, 1), 2)
            last_contact_date = f"{year}-{lc_month:02d}-{random.randint(1,28):02d}"
            area = random.choice(["150㎡", "200㎡", "250㎡", "300㎡", "400㎡", "500㎡", "600㎡", "800㎡"])
            
            new_record = {
                "id": f"CRM_S{i+1:03d}",
                "company_name": ent["name"],
                "contact_person": f"{surname}总",
                "contact_title": title,
                "stage": "已签约",
                "interest_level": random.choice(["高", "高", "中"]),
                "last_contact": last_contact_date,
                "expected_area": area,
                "expected_move_in": "已入驻",
                "notes": [
                    {"date": last_contact_date, "note": f"入驻{building}{floor}，{note}"},
                    {"date": sign_date, "note": f"签约{contract}租赁合同"}
                ]
            }
            CRM_RECORDS.append(new_record)

    for cr in CRM_RECORDS:
        c.execute("INSERT INTO crm_records VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            cr["id"], cr["company_name"], cr["contact_person"],
            cr["contact_title"], cr["stage"], cr["interest_level"],
            cr["last_contact"], cr["expected_area"], cr["expected_move_in"],
            json.dumps(cr["notes"], ensure_ascii=False),
            cr.get("next_follow_up"),
        ))

    conn.commit()
    print(f"[SQLite] 数据库已初始化: {DB_PATH}")
    print(f"  企业: {len(enterprises)} 条")
    print(f"  园区资源: {len(PARK_RESOURCES)} 条")
    print(f"  园区政策: {len(PARK_POLICIES)} 条")
    print(f"  CRM记录: {len(CRM_RECORDS)} 条")
    conn.close()


if __name__ == "__main__":
    init_db()
